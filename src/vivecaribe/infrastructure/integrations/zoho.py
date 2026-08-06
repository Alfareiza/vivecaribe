"""Fetch Zoho Mail order notifications on free accounts (no IMAP/API access).

Playwright is used only for login and cookie / storage_state persistence.
Listing and message reads go through search.do / md.do via context.request.
"""

from __future__ import annotations

import asyncio
import html
import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote

from playwright.async_api import APIResponse, Browser, BrowserContext, Page, Playwright, async_playwright

from vivecaribe.domain.email_message import EmailMessage
from vivecaribe.domain.errors import DomainError
from vivecaribe.logging import logger

TimeWindow = Literal["1h", "24h", "2d", "1m"] | None

ACCOUNT_ID = "2134541000000008002"
MD_READ_CONCURRENCY = 5


class ZohoSession:
    """Playwright login, storage_state persistence, and Zoho Mail API headers."""

    REGION: str = "com"
    SESSION_FILE: Path = Path.home() / ".zohomail_storage.json"

    def __init__(
        self,
        username: str,
        password: str,
        *,
        session_file: Path | None = None,
        account_id: str = ACCOUNT_ID,
    ) -> None:
        """Create a session manager from Zoho login credentials."""
        self.username = username
        self.password = password
        self.session_file = session_file or self.SESSION_FILE
        self.account_id = account_id
        self._meta: dict[str, str] = {}

    @property
    def mail_origin(self) -> str:
        """Return the Zoho Mail origin for this region."""
        return f"https://mail.zoho.{self.REGION}"

    @property
    def _mail_url(self) -> str:
        """Return the Zoho Mail web app URL for this region."""
        return f"{self.mail_origin}/mail"

    @property
    def _accounts_url(self) -> str:
        """Return the Zoho accounts sign-in base URL for this region."""
        return f"https://accounts.zoho.{self.REGION}"

    def load(self) -> dict[str, Any] | None:
        """Load storage_state + meta from disk, or None if missing/invalid."""
        if not self.session_file.exists():
            return None
        try:
            payload = json.loads(self.session_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            logger.warning("Ignoring invalid Zoho session file")
            return None
        if "storage_state" not in payload or "meta" not in payload:
            return None
        self._meta = {str(key): str(value) for key, value in payload["meta"].items()}
        return payload

    def save(self, storage_state: dict[str, Any], meta: dict[str, str]) -> None:
        """Persist storage_state and meta as JSON."""
        self._meta = meta
        self.session_file.write_text(
            json.dumps({"storage_state": storage_state, "meta": meta}),
            encoding="utf-8",
        )

    def api_headers(self) -> dict[str, str]:
        """Build headers required by Zoho Mail XHR endpoints."""
        csrf = self._meta.get("csrf", "")
        if not csrf:
            raise DomainError("Missing CSRF token. Re-login required.")
        return {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": self.mail_origin,
            "referer": f"{self.mail_origin}/zm/",
            "x-requested-with": "XMLHttpRequest",
            "x-zcsrf-token": f"zmrcsr={csrf}",
            "x-zm-version": self._meta.get("static_version", "HS439.4"),
            "x-zm-session": self._meta.get("client_session_id", ""),
        }

    async def _dismiss_post_login_prompts(self, page: Page) -> None:  # pragma: no cover
        """Click through common post-login interstitial buttons when present."""
        for selector in (
            "text=Continue",
            "text=Skip",
            "text=Remind me later",
            "#continuebtn",
        ):
            try:
                await page.click(selector, timeout=2000)
                return
            except Exception:
                continue

    async def login(self, context: BrowserContext) -> None:  # pragma: no cover
        """Sign in with username/password and persist storage_state + meta."""
        page = await context.new_page()
        try:
            await page.goto(
                f"{self._accounts_url}/signin?servicename=ZohoMail",
                wait_until="domcontentloaded",
            )
            await page.fill("#login_id", self.username)
            await page.click("#nextbtn")
            await page.wait_for_selector("#password", state="visible", timeout=15000)
            await page.fill("#password", self.password)
            await page.click("#nextbtn")

            try:
                await page.wait_for_url(
                    lambda url: "tfa-banner" in url
                    or "announcement" in url
                    or "signin" not in url,
                    timeout=15000,
                )
            except Exception:
                pass

            if "tfa-banner" in page.url or "announcement" in page.url:
                await self._dismiss_post_login_prompts(page)

            if "signin" in page.url:
                raise DomainError(
                    "Login failed. Check username/password, or complete 2FA manually.",
                )

            await page.goto(self._mail_url, wait_until="domcontentloaded")
            await page.wait_for_function(
                "() => window.zmail && window.zmail.clientSessionId && window.zmail.accId",
                timeout=20000,
            )
            meta = await page.evaluate(
                """() => ({
                    acc_id: String(zmail.accId || ''),
                    client_session_id: String(zmail.clientSessionId || ''),
                    static_version: String(zmail.staticVersion || 'HS439.4'),
                    csrf: (document.cookie.match(/zmcsr=([^;]+)/) || [])[1] || '',
                })"""
            )
            if not meta.get("csrf"):
                raise DomainError("Login succeeded but zmcsr cookie was not found.")
            if not meta.get("client_session_id"):
                raise DomainError("Login succeeded but clientSessionId was not found.")

            storage_state = await context.storage_state()
            self.save(storage_state, meta)
        finally:
            await page.close()

    async def open_context(
        self,
        playwright: Playwright,
    ) -> tuple[Browser, BrowserContext, bool]:  # pragma: no cover
        """Launch Chromium with restored storage_state when available.

        Returns:
            browser, context, and whether a disk session was loaded (warm path).
        """
        browser = await playwright.chromium.launch(headless=True)
        session = self.load()
        context = await browser.new_context(
            storage_state=session["storage_state"] if session else None,
        )
        return browser, context, session is not None


class ZohoMailClient:
    """HTTP search/read against Zoho Mail using an authenticated Playwright context."""

    FOLDERS_IDS: dict[str, str] = {
        "NOTIFICATIONS": "2134541000000009001",
    }
    LISTING_BATCH_SIZE: int = 100
    TIME_WINDOWS_SECONDS: dict[str, int] = {
        "1h": 60 * 60,
        "24h": 24 * 60 * 60,
        "2d": (24 * 60 * 60) * 2,
        "1m": (24 * 60 * 60) * 30,
    }

    def __init__(self, session: ZohoSession) -> None:
        """Create a mail client bound to a Zoho session."""
        self.session = session

    @staticmethod
    def _encode_search_str(query: str) -> str:
        """Encode a Zoho SearchStr value once, keeping parentheses literal."""
        return quote(query, safe="()")

    @staticmethod
    def _to_search_query(query: str) -> str:
        """Wrap a plain subject substring as Zoho search syntax."""
        return f"Subject = ( {query} )"

    @staticmethod
    def _is_auth_failure(status: int, body: str) -> bool:
        """Return True when the response indicates an expired Zoho session."""
        return status in {401, 403} or "AUTHENTICATION_FAILED" in body

    async def _request_json(
        self,
        context: BrowserContext,
        *,
        method: str,
        url: str,
        form: str | None = None,
        params: dict[str, str] | None = None,
    ) -> object:
        """Perform a Zoho XHR call and parse JSON, raising DomainError on failure."""
        headers = self.session.api_headers()
        response: APIResponse
        if method.upper() == "POST":
            response = await context.request.post(url, data=form or "", headers=headers)
        else:
            response = await context.request.get(url, params=params or {}, headers=headers)

        text = await response.text()
        if self._is_auth_failure(response.status, text):
            raise DomainError("Zoho session expired")
        if response.status >= 400:
            raise DomainError(f"Zoho request failed ({response.status}): {text[:200]}")
        if not text:
            raise DomainError(f"Empty response from {url}")
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise DomainError(
                f"Unexpected response from Zoho API: {text[:200]}",
            ) from exc

    async def search(
        self,
        context: BrowserContext,
        *,
        folder_id: str,
        query: str,
        start: int,
        end: int,
    ) -> list[object]:
        """POST search.do and return the listing payload."""
        body = (
            f"accId={self.session.account_id}"
            f"&thdView=false"
            f"&from={start}"
            f"&to={end}"
            f"&SearchStr={self._encode_search_str(query)}"
            f"&folId={folder_id}"
        )
        payload = await self._request_json(
            context,
            method="POST",
            url=f"{self.session.mail_origin}/zm/search.do",
            form=body,
        )
        if not isinstance(payload, list) or len(payload) < 2:
            raise DomainError("Unexpected Zoho search payload shape")
        return payload

    def _cutoff_ms(self, time_window: TimeWindow) -> int | None:
        """Return epoch-ms cutoff for a time window, or None for no filter.

        Raises:
            DomainError: If ``time_window`` is not a supported value.
        """
        if time_window is None:
            return None
        if time_window not in self.TIME_WINDOWS_SECONDS:
            allowed = ", ".join(repr(key) for key in self.TIME_WINDOWS_SECONDS) + ", or None"
            raise DomainError(
                f"Invalid time_window {time_window!r}. Use one of: {allowed}.",
            )
        return int((time.time() - self.TIME_WINDOWS_SECONDS[time_window]) * 1000)

    @classmethod
    def _summaries(
        cls,
        data: list[object],
        *,
        newer_than_ms: int | None = None,
    ) -> list[dict[str, str | int | bool | datetime]]:
        """Parse listing rows with ``M`` and optionally filter by time."""
        if len(data) < 2 or not isinstance(data[1], list):
            return []

        messages: list[dict[str, str | int | bool | datetime]] = []
        for message in data[1]:
            if not isinstance(message, dict) or "M" not in message:
                continue
            time_ms = int(message.get("LTIME", 0) or 0)
            if newer_than_ms is not None and time_ms < newer_than_ms:
                continue
            messages.append(
                {
                    "id": str(message["M"]),
                    "mail_id": str(message.get("MAILID", "") or ""),
                    "from": str(message.get("F", "") or ""),
                    "subject": html.unescape(str(message.get("SB", "") or "")),
                    "time_ms": time_ms,
                    "unread": message.get("RS", 1) != 1,
                    "received_at": datetime.fromtimestamp(time_ms / 1000, tz=UTC),
                },
            )
        return messages

    @staticmethod
    def _clean_text(raw: str) -> str:
        """Collapse whitespace in a plain-text body."""
        clean = re.sub(r"[\r\n\t]+", " ", raw)
        return re.sub(r" +", " ", clean).strip()

    async def read_message(
        self,
        context: BrowserContext,
        summary: dict[str, str | int | bool | datetime],
        folder_id: str,
    ) -> dict[str, str]:
        """GET md.do for a listing summary row and normalize body fields."""
        payload = await self._request_json(
            context,
            method="GET",
            url=f"{self.session.mail_origin}/zm/md.do",
            params={
                "xhr": str(int(time.time() * 1000)),
                "accId": self.session.account_id,
                "summary": "true",
                "msgId": str(summary["id"]),
                "vfc": "false",
                "split": "true",
                "folId": folder_id,
                "mailId": str(summary["mail_id"]),
            },
        )
        if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], dict):
            raise DomainError("Unexpected Zoho message payload shape")
        message_data = payload[1].get("mdata")
        if not isinstance(message_data, dict):
            raise DomainError("Zoho message payload missing mdata")

        content = str(message_data.get("CONTENT", "") or "")
        return {
            "from": str(message_data.get("FROM", "") or ""),
            "date": str(message_data.get("SENTTIME", "") or ""),
            "body_html": content,
            "body_text": self._clean_text(content),
            "customer_email": str(message_data.get("REPLYTO", "") or ""),
        }

    def _to_email_message(
        self,
        summary: dict[str, str | int | bool | datetime],
        details: dict[str, str],
    ) -> EmailMessage:
        """Normalize a Zoho summary + detail pair into ``EmailMessage``."""
        received_at = summary.get("received_at")
        if not isinstance(received_at, datetime):
            time_ms = int(summary.get("time_ms", 0) or 0)
            received_at = datetime.fromtimestamp(time_ms / 1000, tz=UTC)

        return EmailMessage(
            source="zoho",
            mailbox_message_id=str(summary["id"]),
            sender=details.get("from") or str(summary.get("from", "")),
            recipients=[],
            subject=str(summary.get("subject", "")),
            body_text=details.get("body_text", ""),
            body_html=details.get("body_html", ""),
            received_at=received_at,
            metadata={
                "mail_id": summary.get("mail_id", ""),
                "unread": summary.get("unread", False),
                "customer_email": details.get("customer_email", ""),
            },
        )

    async def _read_many(
        self,
        context: BrowserContext,
        summaries: list[dict[str, str | int | bool | datetime]],
        folder_id: str,
    ) -> list[EmailMessage]:
        """Read message bodies with a small concurrency limit."""
        semaphore = asyncio.Semaphore(MD_READ_CONCURRENCY)

        async def _one(
            summary: dict[str, str | int | bool | datetime],
        ) -> EmailMessage:
            async with semaphore:
                details = await self.read_message(context, summary, folder_id)
                return self._to_email_message(summary, details)

        return list(await asyncio.gather(*(_one(summary) for summary in summaries)))

    async def fetch_emails(
        self,
        context: BrowserContext,
        *,
        query: str,
        folder_name: str,
        time_window: TimeWindow,
        max_results: int,
    ) -> list[EmailMessage]:
        """Search, time-filter, and read matching messages."""
        if folder_name not in self.FOLDERS_IDS:
            raise DomainError(
                f"Unknown folder {folder_name!r}. Known: {', '.join(self.FOLDERS_IDS)}",
            )

        folder_id = self.FOLDERS_IDS[folder_name]
        batch_size = min(max(max_results, 1), self.LISTING_BATCH_SIZE)
        search_query = self._to_search_query(query)
        newer_than_ms = self._cutoff_ms(time_window)

        listing = await self.search(
            context,
            folder_id=folder_id,
            query=search_query,
            start=1,
            end=batch_size,
        )
        summaries = self._summaries(listing, newer_than_ms=newer_than_ms)
        return await self._read_many(context, summaries, folder_id)


class ZohoMailbox:
    """Read Zoho Mail via Playwright auth + HTTP search/read on free-tier accounts.

    Matches the shared mailbox contract ``fetch_messages(*, query, max_results)``.
    Folder and time-window filters are class defaults (not YAML fields).
    """

    FOLDERS_IDS: dict[str, str] = ZohoMailClient.FOLDERS_IDS
    REGION: str = ZohoSession.REGION
    LISTING_BATCH_SIZE: int = ZohoMailClient.LISTING_BATCH_SIZE
    TIME_WINDOWS_SECONDS: dict[str, int] = ZohoMailClient.TIME_WINDOWS_SECONDS
    DEFAULT_TIME_WINDOW: TimeWindow = "1m"
    DEFAULT_FOLDER_NAME: str = "NOTIFICATIONS"
    SESSION_FILE: Path = ZohoSession.SESSION_FILE

    def __init__(
        self,
        username: str,
        password: str,
        *,
        session_file: Path | None = None,
    ) -> None:
        """Create a mailbox client from Zoho login credentials."""
        self.username = username
        self.password = password
        self.session_file = session_file or self.SESSION_FILE
        self._session = ZohoSession(
            username,
            password,
            session_file=self.session_file,
            account_id=ACCOUNT_ID,
        )
        self._client = ZohoMailClient(self._session)

    @property
    def account_id(self) -> str:
        """Return the constant Zoho account id used for mail API calls."""
        return self._session.account_id

    async def fetch_messages(
        self,
        *,
        query: str,
        max_results: int = 30,
    ) -> list[EmailMessage]:
        """Fetch matching emails from the default Zoho folder and time window.

        Args:
            query: Subject substring wrapped as Zoho ``Subject = ( ... )`` search.
            max_results: Caps search.do ``to`` (and thus how many hits are considered).

        Returns:
            Matching emails as normalized ``EmailMessage`` instances.
        """
        async with async_playwright() as playwright:
            browser, context, warm = await self._session.open_context(playwright)
            try:
                if not warm:
                    await self._session.login(context)

                async def _run() -> list[EmailMessage]:
                    return await self._client.fetch_emails(
                        context,
                        query=query,
                        folder_name=self.DEFAULT_FOLDER_NAME,
                        time_window=self.DEFAULT_TIME_WINDOW,
                        max_results=max_results,
                    )

                try:
                    emails = await _run()
                except DomainError as exc:
                    if "session expired" not in str(exc).casefold():
                        raise
                    await self._session.login(context)
                    emails = await _run()

                logger.info(f"Zoho fetched {len(emails)} messages for query={query!r}")
                return emails
            finally:
                await context.close()
                await browser.close()

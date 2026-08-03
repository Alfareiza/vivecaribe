"""Thin Gmail API adapter for fetching and acknowledging messages.

Auth uses Google authorized-user JSON (``token.json`` shape) via ``google-auth``.
Access tokens are refreshed in memory only — credentials are never written back.
HTTP calls stay on the Gmail REST API (same endpoints as the official client).
"""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from vivecaribe.domain.email_message import EmailMessage
from vivecaribe.domain.errors import DomainError
from vivecaribe.logging import logger

_GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"


class GmailMailbox:
    """Fetch and mark messages via the Gmail REST API."""

    def __init__(
        self,
        *,
        credentials_path: Path | None = None,
        credentials_json: str | None = None,
    ) -> None:
        """Create a mailbox client.

        Prefer ``credentials_path`` (local ``secrets/*.json``) or
        ``credentials_json`` (Vercel env var with the same JSON body).
        ``access_token`` remains for tests / one-off callers.
        """
        self._credentials_path = credentials_path
        self._credentials_json = credentials_json
        self._access_token = None
        self._creds: Credentials | None = None
        self._client = None

    def _require_token(self) -> str:
        """Return a valid Bearer access token, refreshing in memory if needed."""
        if self._credentials_path is not None or self._credentials_json:
            return self._access_token_from_oauth()
        if self._access_token:
            return self._access_token
        raise DomainError("Gmail credentials not configured")

    def _load_credentials(self) -> Credentials:
        """Build ``Credentials`` from a file path or an in-memory JSON string."""
        if self._credentials_path is not None:
            path = self._credentials_path
            if not path.is_file():
                raise DomainError(f"Gmail credentials file not found: {path}")
            try:
                return Credentials.from_authorized_user_file(str(path))
            except (OSError, ValueError) as exc:
                raise DomainError(
                    f"Invalid Gmail credentials file: {path}",
                ) from exc

        assert self._credentials_json is not None
        try:
            info: dict[str, Any] = json.loads(self._credentials_json)
            return Credentials.from_authorized_user_info(info)
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            raise DomainError("Invalid Gmail credentials JSON") from exc

    def _refresh_credentials(self) -> None:
        """Refresh the access token in memory (never writes credentials back)."""
        assert self._creds is not None
        if not self._creds.refresh_token:
            raise DomainError(
                "Gmail credentials expired and cannot be refreshed; re-authorize",
            )
        try:
            self._creds.refresh(Request())
        except Exception as exc:
            raise DomainError(
                "Gmail token refresh failed; re-authorize the mailbox",
            ) from exc
        logger.info("Refreshed Gmail access token in memory")

    def _access_token_from_oauth(self) -> str:
        """Load OAuth credentials and return a usable access token.

        Always refreshes once on first load when a ``refresh_token`` is present.
        Stored ``token``/``expiry`` in JSON can be stale (we never rewrite the
        file after refresh), which otherwise makes ``Credentials.valid`` trust a
        dead access token and Gmail returns HTTP 401.
        """
        if self._creds is None:
            self._creds = self._load_credentials()
            if self._creds.refresh_token:
                self._refresh_credentials()
            elif not self._creds.valid:
                raise DomainError(
                    "Gmail credentials expired and cannot be refreshed; re-authorize",
                )
        elif not self._creds.valid:
            if self._creds.expired:
                self._refresh_credentials()
            else:
                raise DomainError(
                    "Gmail credentials expired and cannot be refreshed; re-authorize",
                )

        if not self._creds.token:
            raise DomainError("Gmail credentials have no access token")
        return self._creds.token

    def _headers(self) -> dict[str, str]:
        """Build Authorization headers for Gmail API calls."""
        return {"Authorization": f"Bearer {self._require_token()}"}

    async def _http(self) -> httpx.AsyncClient:
        """Return the injected client or a short-lived default client."""
        if self._client is not None:
            return self._client
        return httpx.AsyncClient(timeout=30.0)

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        reraise=True,
    )
    async def fetch_messages(
        self,
        *,
        query: str,
        max_results: int = 30,
    ) -> list[EmailMessage]:
        """List messages matching ``query`` and load full MIME payloads."""
        owns_client = self._client is None
        client = await self._http()
        try:
            listed = await client.get(
                f"{_GMAIL_API}/messages",
                params={"q": query, "maxResults": max_results},
                headers=self._headers(),
            )
            if listed.status_code >= 400:
                raise DomainError(
                    f"Gmail list failed: HTTP {listed.status_code}",
                )
            ids = [item["id"] for item in listed.json().get("messages", [])]
            messages: list[EmailMessage] = []
            for message_id in ids:
                messages.append(await self._load_message(client, message_id))
            logger.info(f"Gmail fetched {len(messages)} messages for query={query!r}")
            return messages
        finally:
            if owns_client:
                await client.aclose()

    async def _load_message(
        self,
        client: httpx.AsyncClient,
        message_id: str,
    ) -> EmailMessage:
        """Fetch one Gmail message and normalize it to ``EmailMessage``."""
        response = await client.get(
            f"{_GMAIL_API}/messages/{message_id}",
            params={"format": "full"},
            headers=self._headers(),
        )
        if response.status_code >= 400:
            raise DomainError(
                f"Gmail get message failed: HTTP {response.status_code}",
            )
        payload = response.json()
        headers = {
            h["name"].lower(): h["value"]
            for h in payload.get("payload", {}).get("headers", [])
        }
        body_html, body_text = _extract_bodies(payload.get("payload", {}))
        received = _parse_internal_date(payload.get("internalDate"))
        return EmailMessage(
            source="gmail",
            mailbox_message_id=message_id,
            sender=headers.get("from", ""),
            recipients=_split_addresses(headers.get("to", "")),
            subject=headers.get("subject", ""),
            body_text=body_text,
            body_html=body_html,
            received_at=received,
            metadata={"thread_id": payload.get("threadId")},
        )

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        reraise=True,
    )
    async def mark_as_read(self, *, mailbox_message_id: str) -> None:
        """Remove the UNREAD label from ``mailbox_message_id``."""
        owns_client = self._client is None
        client = await self._http()
        try:
            response = await client.post(
                f"{_GMAIL_API}/messages/{mailbox_message_id}/modify",
                headers=self._headers(),
                json={"removeLabelIds": ["UNREAD"]},
            )
            if response.status_code >= 400:
                raise DomainError(
                    f"Gmail mark_as_read failed: HTTP {response.status_code}",
                )
        finally:
            if owns_client:
                await client.aclose()


def _split_addresses(raw: str) -> list[str]:
    """Split a comma-separated address header into individual emails."""
    return [part.strip() for part in raw.split(",") if part.strip()]


def _parse_internal_date(raw: str | int | None) -> datetime:
    """Convert Gmail ``internalDate`` (ms epoch) to an aware UTC datetime."""
    if raw is None:
        return datetime.now(UTC)
    try:
        return datetime.fromtimestamp(int(raw) / 1000, tz=UTC)
    except (TypeError, ValueError):
        return datetime.now(UTC)


def _extract_bodies(payload: dict) -> tuple[str, str]:
    """Return ``(body_html, body_text)`` from a Gmail message payload tree."""
    html = ""
    text = ""

    def walk(part: dict) -> None:
        nonlocal html, text
        mime = part.get("mimeType", "")
        data = part.get("body", {}).get("data")
        if data:
            decoded = base64.urlsafe_b64decode(data + "==").decode(
                "utf-8",
                errors="replace",
            )
            if mime == "text/html" and not html:
                html = decoded
            elif mime == "text/plain" and not text:
                text = decoded
        for child in part.get("parts") or []:
            walk(child)

    walk(payload)
    return html, text

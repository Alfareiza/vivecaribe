"""Thin Microsoft Graph (Outlook) adapter for fetching and acknowledging mail.

Auth uses MSAL ``ConfidentialClientApplication`` + refresh token (consumers
authority). Access tokens are acquired in memory only — refresh tokens are
never written back to disk or env.
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import msal
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from vivecaribe.domain.email_message import EmailMessage
from vivecaribe.domain.errors import DomainError
from vivecaribe.logging import logger

_GRAPH_API = "https://graph.microsoft.com/v1.0/me"
_AUTHORITY = "https://login.microsoftonline.com/consumers"


class OutlookMailbox:
    """Fetch and mark messages via Microsoft Graph mail API."""

    SCOPES: tuple[str, ...] = ("User.Read", "Mail.ReadWrite")

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        source: str = "outlook",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Create a mailbox client backed by MSAL refresh-token auth."""
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._access_token: str | None = None
        self._source = source
        self._client = client

    def _acquire_access_token(self) -> str:
        """Exchange the refresh token for a Graph access token (in memory)."""
        app = msal.ConfidentialClientApplication(
            client_id=self._client_id,
            client_credential=self._client_secret,
            authority=_AUTHORITY,
        )
        result = app.acquire_token_by_refresh_token(
            self._refresh_token,
            scopes=list(self.SCOPES),
        )
        access_token = result.get("access_token") if isinstance(result, dict) else None
        if not access_token:
            error = result.get("error_description") or result.get("error") or result
            raise DomainError(f"Outlook token refresh failed: {error}")
        logger.info("Acquired Outlook access token via MSAL refresh token")
        return access_token

    def _require_token(self) -> str:
        """Return a cached access token, acquiring one via MSAL when needed."""
        if not self._access_token:
            self._access_token = self._acquire_access_token()
        return self._access_token

    def _headers(self) -> dict[str, str]:
        """Build Authorization headers for Graph API calls."""
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
        """Search messages with a KQL ``query`` and normalize to ``EmailMessage``."""
        owns_client = self._client is None
        client = await self._http()
        try:
            response = await client.get(
                f"{_GRAPH_API}/messages",
                params={
                    "$search": f'"{query}"',
                    "$top": str(max_results),
                    "$select": (
                        "id,subject,from,toRecipients,body,bodyPreview,"
                        "receivedDateTime"
                    ),
                },
                headers={
                    **self._headers(),
                    "ConsistencyLevel": "eventual",
                },
            )
            if response.status_code >= 400:
                raise DomainError(
                    f"Outlook list failed: HTTP {response.status_code}",
                )
            messages = [
                self._to_email_message(item) for item in response.json().get("value", [])
            ]
            logger.info(
                "Outlook fetched %s messages for query=%s",
                len(messages),
                query,
            )
            return messages
        finally:
            if owns_client:
                await client.aclose()

    def _to_email_message(self, item: dict) -> EmailMessage:
        """Map a Graph message JSON object to domain ``EmailMessage``."""
        sender = (
            item.get("from", {})
            .get("emailAddress", {})
            .get("address", "")
        )
        recipients = [
            r.get("emailAddress", {}).get("address", "")
            for r in item.get("toRecipients", [])
            if r.get("emailAddress", {}).get("address")
        ]
        body = item.get("body") or {}
        content_type = (body.get("contentType") or "").lower()
        content = body.get("content") or ""
        body_html = content if content_type == "html" else ""
        body_text = (
            content if content_type != "html" else (item.get("bodyPreview") or "")
        )
        received_raw = item.get("receivedDateTime")
        if received_raw:
            received = datetime.fromisoformat(received_raw.replace("Z", "+00:00"))
        else:
            received = datetime.now(UTC)
        return EmailMessage(
            source=self._source,
            mailbox_message_id=item["id"],
            sender=sender,
            recipients=recipients,
            subject=item.get("subject") or "",
            body_text=body_text,
            body_html=body_html,
            received_at=received,
            metadata={},
        )

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        reraise=True,
    )
    async def mark_as_read(self, *, mailbox_message_id: str) -> None:
        """Set ``isRead=true`` on the Graph message."""
        owns_client = self._client is None
        client = await self._http()
        try:
            response = await client.patch(
                f"{_GRAPH_API}/messages/{mailbox_message_id}",
                headers=self._headers(),
                json={"isRead": True},
            )
            if response.status_code >= 400:
                raise DomainError(
                    f"Outlook mark_as_read failed: HTTP {response.status_code}",
                )
        finally:
            if owns_client:
                await client.aclose()

"""Thin Microsoft Graph (Outlook) adapter for fetching and acknowledging mail.

Credentials are constructor-injected (Settings env wiring comes later).
Without an access token, calls fail with a clear domain error.
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from vivecaribe.domain.email_message import EmailMessage
from vivecaribe.domain.errors import DomainError
from vivecaribe.logging import logger

_GRAPH_API = "https://graph.microsoft.com/v1.0/me"


class OutlookMailbox:
    """Fetch and mark messages via Microsoft Graph mail API."""

    def __init__(
        self,
        *,
        access_token: str | None = None,
        source: str = "outlook",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Create a mailbox client; ``access_token`` is required for live calls."""
        self._access_token = access_token
        self._source = source
        self._client = client

    def _require_token(self) -> str:
        """Return the access token or raise if credentials are missing."""
        if not self._access_token:
            raise DomainError("Outlook credentials not configured")
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

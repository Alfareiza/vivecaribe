"""Gmail OAuth auth, HTTP fetch/mark, and payload helpers."""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import httpx
import pytest

from vivecaribe.domain.errors import DomainError
from vivecaribe.infrastructure.integrations.gmail import (
    GmailMailbox,
    _extract_bodies,
    _parse_internal_date,
    _split_addresses,
)
from vivecaribe.settings import MailboxConfig, get_settings


def _b64(text: str) -> str:
    """Encode text the way Gmail returns body data."""
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


def _gmail_mailbox(client: httpx.AsyncClient | None = None) -> GmailMailbox:
    return GmailMailbox(
        token="stale",
        refresh_token="refresh",
        client_id="id",
        client_secret="secret",
        client=client,
    )


def _patch_token(mailbox: GmailMailbox) -> MagicMock:
    fake_creds = MagicMock()
    fake_creds.refresh_token = "refresh"
    fake_creds.valid = True
    fake_creds.token = "fresh-token"
    return patch.object(mailbox, "_build_credentials", return_value=fake_creds)


def test_gmail_require_token_refreshes_on_first_use() -> None:
    """First token request always refreshes (avoids stale env access tokens)."""
    mailbox = _gmail_mailbox()
    fake_creds = MagicMock()
    fake_creds.refresh_token = "refresh"
    fake_creds.valid = True
    fake_creds.token = "fresh-token"
    with patch.object(mailbox, "_build_credentials", return_value=fake_creds):
        token = mailbox._require_token()
        again = mailbox._require_token()

    assert token == "fresh-token"
    assert again == "fresh-token"
    fake_creds.refresh.assert_called_once()


def test_gmail_refresh_failure_raises_domain_error() -> None:
    """Refresh failures surface as DomainError."""
    mailbox = _gmail_mailbox()
    fake_creds = MagicMock()
    fake_creds.refresh_token = "refresh"
    fake_creds.refresh.side_effect = RuntimeError("boom")

    with patch.object(mailbox, "_build_credentials", return_value=fake_creds):
        with pytest.raises(DomainError, match="token refresh failed"):
            mailbox._require_token()


def test_gmail_require_token_no_refresh_token() -> None:
    """Missing refresh token cannot recover an expired credential."""
    mailbox = _gmail_mailbox()
    fake_creds = MagicMock()
    fake_creds.refresh_token = ""
    with patch.object(mailbox, "_build_credentials", return_value=fake_creds):
        with pytest.raises(DomainError, match="cannot be refreshed"):
            mailbox._require_token()


def test_gmail_require_token_invalid_not_expired() -> None:
    """Invalid but non-expired credentials raise without refreshing again."""
    mailbox = _gmail_mailbox()
    fake_creds = MagicMock()
    fake_creds.refresh_token = "refresh"
    fake_creds.valid = False
    fake_creds.expired = False
    fake_creds.token = "x"
    mailbox._creds = fake_creds
    with pytest.raises(DomainError, match="cannot be refreshed"):
        mailbox._require_token()


def test_gmail_require_token_empty_access_token() -> None:
    """Credentials without an access token raise DomainError."""
    mailbox = _gmail_mailbox()
    fake_creds = MagicMock()
    fake_creds.refresh_token = "refresh"
    fake_creds.valid = True
    fake_creds.token = ""
    with patch.object(mailbox, "_build_credentials", return_value=fake_creds):
        with pytest.raises(DomainError, match="no access token"):
            mailbox._require_token()


def test_gmail_require_token_refreshes_when_expired() -> None:
    """Expired credentials after first load are refreshed again."""
    mailbox = _gmail_mailbox()
    fake_creds = MagicMock()
    fake_creds.refresh_token = "refresh"
    fake_creds.valid = False
    fake_creds.expired = True
    fake_creds.token = "after-refresh"
    mailbox._creds = fake_creds
    token = mailbox._require_token()
    assert token == "after-refresh"
    fake_creds.refresh.assert_called_once()


def test_split_addresses() -> None:
    """Comma-separated address headers become a clean list."""
    assert _split_addresses("a@x.com, b@y.com") == ["a@x.com", "b@y.com"]
    assert _split_addresses("") == []


def test_parse_internal_date_valid_and_fallbacks() -> None:
    """Valid ms epochs parse; None/bad values fall back to now UTC."""
    assert _parse_internal_date("1700000000000") == datetime.fromtimestamp(
        1700000000,
        tz=UTC,
    )
    assert _parse_internal_date(None).tzinfo is UTC
    assert _parse_internal_date("not-a-number").tzinfo is UTC


def test_extract_bodies_multipart_nested() -> None:
    """Nested MIME parts yield both HTML and plain text."""
    payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {
                "mimeType": "multipart/alternative",
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {"data": _b64("plain body")},
                    },
                    {
                        "mimeType": "text/html",
                        "body": {"data": _b64("<p>html body</p>")},
                    },
                ],
            },
        ],
    }
    html, text = _extract_bodies(payload)
    assert html == "<p>html body</p>"
    assert text == "plain body"


@pytest.mark.asyncio
async def test_gmail_fetch_messages_happy_path() -> None:
    """List + get message normalize into EmailMessage."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/messages") and request.method == "GET":
            return httpx.Response(200, json={"messages": [{"id": "m1"}]})
        if request.url.path.endswith("/messages/m1"):
            return httpx.Response(
                200,
                json={
                    "id": "m1",
                    "threadId": "t1",
                    "internalDate": "1700000000000",
                    "payload": {
                        "headers": [
                            {"name": "From", "value": "a@b.com"},
                            {"name": "To", "value": "ops@vivecaribe.com"},
                            {"name": "Subject", "value": "Booking"},
                        ],
                        "mimeType": "text/html",
                        "body": {"data": _b64("<p>hi</p>")},
                    },
                },
            )
        return httpx.Response(404, json={"error": "unexpected"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        mailbox = _gmail_mailbox(client)
        with _patch_token(mailbox):
            messages = await mailbox.fetch_messages(query="from:x", max_results=10)

    assert len(messages) == 1
    assert messages[0].mailbox_message_id == "m1"
    assert messages[0].sender == "a@b.com"
    assert messages[0].subject == "Booking"
    assert messages[0].body_html == "<p>hi</p>"
    assert messages[0].metadata == {"thread_id": "t1"}


@pytest.mark.asyncio
async def test_gmail_fetch_messages_list_http_error() -> None:
    """List HTTP >= 400 becomes DomainError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        mailbox = _gmail_mailbox(client)
        with _patch_token(mailbox):
            with pytest.raises(DomainError, match="list failed"):
                await mailbox.fetch_messages(query="x")


@pytest.mark.asyncio
async def test_gmail_load_message_http_error() -> None:
    """Get-message HTTP >= 400 becomes DomainError."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/messages") and request.method == "GET":
            return httpx.Response(200, json={"messages": [{"id": "m1"}]})
        return httpx.Response(404, json={"error": "missing"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        mailbox = _gmail_mailbox(client)
        with _patch_token(mailbox):
            with pytest.raises(DomainError, match="get message failed"):
                await mailbox.fetch_messages(query="x")


@pytest.mark.asyncio
async def test_gmail_mark_as_read_success() -> None:
    """Successful modify call completes without error."""
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        mailbox = _gmail_mailbox(client)
        with _patch_token(mailbox):
            await mailbox.mark_as_read(mailbox_message_id="m1")

    assert str(seen["path"]).endswith("/messages/m1/modify")
    assert seen["body"] == {"removeLabelIds": ["UNREAD"]}


@pytest.mark.asyncio
async def test_gmail_mark_as_read_http_error() -> None:
    """Mark-as-read HTTP >= 400 becomes DomainError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": "denied"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        mailbox = _gmail_mailbox(client)
        with _patch_token(mailbox):
            with pytest.raises(DomainError, match="mark_as_read failed"):
                await mailbox.mark_as_read(mailbox_message_id="m1")


def test_mailbox_config_builds_gmail_from_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gmail mailbox wires OAuth inputs from Settings / env."""
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("JWT_SECRET", "secret")
    monkeypatch.setenv("CRON_SECRET", "cron")
    monkeypatch.setenv("GMAIL_CLIENT_ID", "gmail-id")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "gmail-secret")
    monkeypatch.setenv("GYG_GMAIL_TOKEN", "access")
    monkeypatch.setenv("GYG_GMAIL_REFRESH_TOKEN", "refresh")

    config = MailboxConfig(
        mailbox_name="gmail",
        credentials_vars={
            "token": "GYG_GMAIL_TOKEN",
            "refresh_token": "GYG_GMAIL_REFRESH_TOKEN",
        },
        queries={"new_bookings_query": "x"},
    )
    client = config.client

    assert isinstance(client, GmailMailbox)
    assert client._token == "access"
    assert client._refresh_token == "refresh"
    assert client._client_id == "gmail-id"
    assert client._client_secret == "gmail-secret"
    # Second access reuses the cached client.
    assert config.client is client
    get_settings.cache_clear()


def test_mailbox_config_missing_credentials_var_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing credentials_vars keys raise before reading env."""
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("JWT_SECRET", "secret")
    monkeypatch.setenv("CRON_SECRET", "cron")
    monkeypatch.setenv("GMAIL_CLIENT_ID", "gmail-id")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "gmail-secret")

    config = MailboxConfig(
        mailbox_name="gmail",
        credentials_vars={"token": "GYG_GMAIL_TOKEN"},
        queries={"new_bookings_query": "x"},
    )
    with pytest.raises(DomainError, match="refresh_token"):
        _ = config.client
    get_settings.cache_clear()

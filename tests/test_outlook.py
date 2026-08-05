"""Outlook MSAL auth, Graph fetch/mark, and message mapping."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from vivecaribe.domain.errors import DomainError
from vivecaribe.infrastructure.integrations.outlook import OutlookMailbox
from vivecaribe.settings import MailboxConfig, Settings, get_settings


def _outlook_mailbox(client: httpx.AsyncClient | None = None) -> OutlookMailbox:
    return OutlookMailbox(
        client_id="id",
        client_secret="secret",
        refresh_token="refresh",
        client=client,
    )


def _patch_msal(access_token: str = "access-abc") -> MagicMock:
    fake_app = MagicMock()
    fake_app.acquire_token_by_refresh_token.return_value = {
        "access_token": access_token,
    }
    return patch(
        "vivecaribe.infrastructure.integrations.outlook.msal.ConfidentialClientApplication",
        return_value=fake_app,
    )


def test_settings_require_env_reads_value(monkeypatch: pytest.MonkeyPatch) -> None:
    """``require_env`` returns a configured environment variable."""
    monkeypatch.setenv("HOMEFANS_OUTLOOK_REFRESH_TOKEN", "refresh-xyz")
    assert Settings.require_env("HOMEFANS_OUTLOOK_REFRESH_TOKEN") == "refresh-xyz"


def test_settings_require_env_missing_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing env vars raise a clear domain error."""
    monkeypatch.delenv("HOMEFANS_OUTLOOK_REFRESH_TOKEN", raising=False)
    with pytest.raises(DomainError, match="HOMEFANS_OUTLOOK_REFRESH_TOKEN"):
        Settings.require_env("HOMEFANS_OUTLOOK_REFRESH_TOKEN")


def test_outlook_acquire_access_token_via_msal() -> None:
    """MSAL refresh-token exchange caches the access token in memory."""
    mailbox = _outlook_mailbox()
    with _patch_msal() as ctor:
        token = mailbox._require_token()
        again = mailbox._require_token()

    assert token == "access-abc"
    assert again == "access-abc"
    ctor.assert_called_once()


def test_outlook_acquire_access_token_failure() -> None:
    """MSAL error payload becomes a DomainError."""
    mailbox = _outlook_mailbox()
    fake_app = MagicMock()
    fake_app.acquire_token_by_refresh_token.return_value = {
        "error": "invalid_grant",
        "error_description": "refresh gone",
    }

    with patch(
        "vivecaribe.infrastructure.integrations.outlook.msal.ConfidentialClientApplication",
        return_value=fake_app,
    ):
        with pytest.raises(DomainError, match="refresh gone"):
            mailbox._require_token()


def test_to_email_message_html_and_plain() -> None:
    """HTML bodies keep content; plain bodies use content / preview."""
    mailbox = OutlookMailbox(
        client_id="id",
        client_secret="secret",
        refresh_token="refresh",
        source="homefans",
    )
    html_msg = mailbox._to_email_message(
        {
            "id": "1",
            "subject": "Order",
            "from": {"emailAddress": {"address": "a@h.com"}},
            "toRecipients": [{"emailAddress": {"address": "ops@v.com"}}],
            "body": {"contentType": "html", "content": "<p>hi</p>"},
            "bodyPreview": "hi",
            "receivedDateTime": "2026-07-01T12:00:00Z",
        },
    )
    assert html_msg.source == "homefans"
    assert html_msg.body_html == "<p>hi</p>"
    assert html_msg.body_text == "hi"
    assert html_msg.sender == "a@h.com"

    plain_msg = mailbox._to_email_message(
        {
            "id": "2",
            "subject": "Order",
            "from": {"emailAddress": {"address": "a@h.com"}},
            "toRecipients": [],
            "body": {"contentType": "text", "content": "plain"},
            "receivedDateTime": None,
        },
    )
    assert plain_msg.body_html == ""
    assert plain_msg.body_text == "plain"
    assert plain_msg.received_at.tzinfo is not None


@pytest.mark.asyncio
async def test_outlook_fetch_messages_happy_path() -> None:
    """Graph list response maps into EmailMessage list."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "id": "oid-1",
                        "subject": "New order",
                        "from": {"emailAddress": {"address": "x@homefans.net"}},
                        "toRecipients": [
                            {"emailAddress": {"address": "ops@vivecaribe.com"}},
                        ],
                        "body": {"contentType": "html", "content": "<b>ok</b>"},
                        "bodyPreview": "ok",
                        "receivedDateTime": "2026-07-01T12:00:00Z",
                    },
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        mailbox = _outlook_mailbox(client)
        with _patch_msal():
            messages = await mailbox.fetch_messages(query="from:homefans", max_results=5)

    assert len(messages) == 1
    assert messages[0].mailbox_message_id == "oid-1"
    assert messages[0].body_html == "<b>ok</b>"


@pytest.mark.asyncio
async def test_outlook_fetch_messages_http_error() -> None:
    """List HTTP >= 400 becomes DomainError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "denied"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        mailbox = _outlook_mailbox(client)
        with _patch_msal():
            with pytest.raises(DomainError, match="list failed"):
                await mailbox.fetch_messages(query="x")


@pytest.mark.asyncio
async def test_outlook_mark_as_read_success_and_error() -> None:
    """PATCH success completes; HTTP error becomes DomainError."""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(200, json={})
        return httpx.Response(500, json={"error": "x"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        mailbox = _outlook_mailbox(client)
        with _patch_msal():
            await mailbox.mark_as_read(mailbox_message_id="oid-1")
            with pytest.raises(DomainError, match="mark_as_read failed"):
                await mailbox.mark_as_read(mailbox_message_id="oid-2")


def test_mailbox_config_builds_outlook_from_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Outlook mailbox wires MSAL inputs from Settings / env."""
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("JWT_SECRET", "secret")
    monkeypatch.setenv("CRON_SECRET", "cron")
    monkeypatch.setenv("OUTLOOK_CLIENT_ID", "app-id")
    monkeypatch.setenv("OUTLOOK_CLIENT_SECRET", "app-secret")
    monkeypatch.setenv("HOMEFANS_OUTLOOK_REFRESH_TOKEN", "refresh-token")

    config = MailboxConfig(
        mailbox_name="outlook",
        credentials_vars={"refresh_token": "HOMEFANS_OUTLOOK_REFRESH_TOKEN"},
        queries={"new_bookings_query": "x"},
    )
    client = config.client

    assert isinstance(client, OutlookMailbox)
    assert client._client_id == "app-id"
    assert client._client_secret == "app-secret"
    assert client._refresh_token == "refresh-token"
    get_settings.cache_clear()

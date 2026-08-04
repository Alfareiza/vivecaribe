"""Gmail OAuth auth and settings helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from vivecaribe.domain.errors import DomainError
from vivecaribe.infrastructure.integrations.gmail import GmailMailbox
from vivecaribe.settings import MailboxConfig, get_settings


def test_gmail_require_token_refreshes_on_first_use() -> None:
    """First token request always refreshes (avoids stale env access tokens)."""
    mailbox = GmailMailbox(
        token="stale",
        refresh_token="refresh",
        client_id="id",
        client_secret="secret",
    )
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
    mailbox = GmailMailbox(
        token="stale",
        refresh_token="refresh",
        client_id="id",
        client_secret="secret",
    )
    fake_creds = MagicMock()
    fake_creds.refresh_token = "refresh"
    fake_creds.refresh.side_effect = RuntimeError("boom")

    with patch.object(mailbox, "_build_credentials", return_value=fake_creds):
        with pytest.raises(DomainError, match="token refresh failed"):
            mailbox._require_token()


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

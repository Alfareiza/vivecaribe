"""Outlook MSAL auth and settings helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from vivecaribe.domain.errors import DomainError
from vivecaribe.infrastructure.integrations.outlook import OutlookMailbox
from vivecaribe.settings import MailboxConfig, Settings, get_settings


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
    mailbox = OutlookMailbox(
        client_id="id",
        client_secret="secret",
        refresh_token="refresh",
    )
    fake_app = MagicMock()
    fake_app.acquire_token_by_refresh_token.return_value = {
        "access_token": "access-abc",
    }

    with patch(
        "vivecaribe.infrastructure.integrations.outlook.msal.ConfidentialClientApplication",
        return_value=fake_app,
    ) as ctor:
        token = mailbox._require_token()
        again = mailbox._require_token()

    assert token == "access-abc"
    assert again == "access-abc"
    ctor.assert_called_once()
    fake_app.acquire_token_by_refresh_token.assert_called_once_with(
        "refresh",
        scopes=list(OutlookMailbox.SCOPES),
    )


def test_outlook_acquire_access_token_failure() -> None:
    """MSAL error payload becomes a DomainError."""
    mailbox = OutlookMailbox(
        client_id="id",
        client_secret="secret",
        refresh_token="refresh",
    )
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

"""Settings and booking_providers.yaml loading."""

from pathlib import Path

import pytest

from vivecaribe.domain.errors import DomainError
from vivecaribe.settings import Settings, get_settings


def test_get_settings_is_cached() -> None:
    """``get_settings`` returns the same cached instance across calls."""
    first = get_settings()
    second = get_settings()
    assert first is second


def test_load_booking_providers_from_repo_yaml() -> None:
    """``load_booking_providers`` parses the repository YAML stub."""
    settings = Settings(
        database_url="postgresql+psycopg://u:p@localhost/db",
        jwt_secret="secret",
        cron_secret="cron",
    )
    config = settings.load_booking_providers()

    assert len(config.booking_providers) >= 1
    first = config.booking_providers[0]
    assert first.mailbox.mailbox_name in {"gmail", "outlook"}
    assert "new_bookings_query" in first.mailbox.queries
    assert first.mailbox.credentials_vars


def test_settings_validators_normalize_log_level_and_blank_sentry() -> None:
    """Validators uppercase log level and treat blank Sentry DSN as unset."""
    settings = Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        jwt_secret="secret",
        cron_secret="cron",
        log_level="debug",
        sentry_dsn="  ",
        gmail_client_id="",
    )
    assert settings.log_level == "DEBUG"
    assert settings.sentry_dsn is None
    assert settings.gmail_client_id is None


def test_require_gmail_and_outlook_credentials_raise_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing shared OAuth app credentials raise DomainError."""
    for name in (
        "GMAIL_CLIENT_ID",
        "GMAIL_CLIENT_SECRET",
        "OUTLOOK_CLIENT_ID",
        "OUTLOOK_CLIENT_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://u:p@localhost/db",
        jwt_secret="secret",
        cron_secret="cron",
    )
    with pytest.raises(DomainError, match="GMAIL_CLIENT_ID"):
        settings.require_gmail_client_id()
    with pytest.raises(DomainError, match="GMAIL_CLIENT_SECRET"):
        settings.require_gmail_client_secret()
    with pytest.raises(DomainError, match="OUTLOOK_CLIENT_ID"):
        settings.require_outlook_client_id()
    with pytest.raises(DomainError, match="OUTLOOK_CLIENT_SECRET"):
        settings.require_outlook_client_secret()


def test_load_booking_providers_missing_file_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Missing YAML path yields an empty booking-provider list."""
    monkeypatch.chdir(tmp_path)
    settings = Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        jwt_secret="secret",
        cron_secret="cron",
    )
    assert settings.load_booking_providers().booking_providers == []

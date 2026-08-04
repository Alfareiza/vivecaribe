"""Settings and booking_providers.yaml loading."""

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

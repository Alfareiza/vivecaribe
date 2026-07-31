"""Settings and accounts.yaml loading."""

from pathlib import Path

from vivecaribe.settings import Settings, get_settings


def test_get_settings_is_cached() -> None:
    """``get_settings`` returns the same cached instance across calls."""
    first = get_settings()
    second = get_settings()
    assert first is second


def test_load_accounts_from_repo_yaml() -> None:
    """``load_accounts`` parses the repository ``accounts.yaml`` stub."""
    settings = Settings(
        database_url="postgresql+psycopg://u:p@localhost/db",
        jwt_secret="secret",
        cron_secret="cron",
        accounts_yaml_path=Path("accounts.yaml"),
    )
    accounts = settings.load_accounts()

    assert len(accounts.accounts) >= 1
    assert accounts.accounts[0].provider in {"gmail", "outlook"}
    assert accounts.accounts[0].queries

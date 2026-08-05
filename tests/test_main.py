"""Application factory, lifespan, and Sentry init."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vivecaribe.main import _init_sentry, create_app, lifespan
from vivecaribe.settings import get_settings


def test_create_app_includes_routers() -> None:
    """App factory mounts health, auth, and automation routes."""
    paths = set(create_app().openapi()["paths"])
    assert "/health" in paths
    assert "/users" in paths
    assert "/login" in paths
    assert "/automation/emails/get-bookings" in paths


def test_init_sentry_skips_when_dsn_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Blank Sentry DSN leaves the SDK uninitialized."""
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("JWT_SECRET", "secret")
    monkeypatch.setenv("CRON_SECRET", "cron")
    monkeypatch.setenv("SENTRY_DSN", "")
    with patch("vivecaribe.main.sentry_sdk.init") as init:
        _init_sentry()
    init.assert_not_called()
    get_settings.cache_clear()


def test_init_sentry_initializes_when_dsn_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configured DSN initializes Sentry with env-specific sample rates."""
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("JWT_SECRET", "secret")
    monkeypatch.setenv("CRON_SECRET", "cron")
    monkeypatch.setenv("SENTRY_DSN", "https://key@example.com/1")
    monkeypatch.setenv("ENVIRONMENT", "prod")
    with patch("vivecaribe.main.sentry_sdk.init") as init:
        _init_sentry()
    init.assert_called_once()
    assert init.call_args.kwargs["traces_sample_rate"] == 0.2
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_lifespan_startup_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lifespan configures logging, initializes DB, then disposes it."""
    get_settings.cache_clear()
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5433/vivecaribe_test",
    )
    monkeypatch.setenv("JWT_SECRET", "secret")
    monkeypatch.setenv("CRON_SECRET", "cron")

    app = create_app()
    with (
        patch("vivecaribe.main.configure_logging") as configure,
        patch("vivecaribe.api.deps.init_db", return_value=MagicMock()) as init_db,
        patch(
            "vivecaribe.api.deps.shutdown_db",
            new_callable=AsyncMock,
        ) as shut,
    ):
        async with lifespan(app):
            pass

    configure.assert_called_once()
    init_db.assert_called_once()
    shut.assert_awaited_once()
    get_settings.cache_clear()

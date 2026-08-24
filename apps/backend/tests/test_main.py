"""Application factory, lifespan, and Sentry init."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from vivecaribe.main import _init_sentry, create_app, lifespan
from vivecaribe.settings import get_settings


def test_create_app_includes_routers() -> None:
    """App factory mounts health, auth, and automation routes."""
    paths = set(create_app().openapi()["paths"])
    assert "/health" in paths
    assert "/users" in paths
    assert "/login" in paths
    assert "/refresh" in paths
    assert "/logout" in paths
    assert "/automation/emails/get-bookings" in paths


def test_create_app_adds_cors_when_origins_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CORS middleware is mounted when ``CORS_ORIGINS`` is set."""
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("JWT_SECRET", "secret")
    monkeypatch.setenv("CRON_SECRET", "cron")
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "http://localhost:3000,https://vivecaribe-frontend.vercel.app",
    )
    app = create_app()
    assert any(
        getattr(middleware.cls, "__name__", "") == "CORSMiddleware"
        for middleware in app.user_middleware
    )
    get_settings.cache_clear()


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
    assert init.call_args.kwargs["traces_sample_rate"] == 1.0
    get_settings.cache_clear()


def test_validation_error_is_reported_to_sentry() -> None:
    """A bad request body reaches Sentry and still returns the usual 422.

    FastAPI answers these itself, so the Sentry integration never sees them
    (it only auto-captures 5xx); without our handler they are invisible.
    """
    client = TestClient(create_app())
    with patch("vivecaribe.main.sentry_sdk.capture_exception") as capture:
        response = client.post("/users", json={"email": 42, "password": "x"})

    assert response.status_code == 422
    capture.assert_called_once()
    assert isinstance(capture.call_args.args[0], RequestValidationError)


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

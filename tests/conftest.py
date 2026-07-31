"""Shared pytest fixtures."""

from __future__ import annotations

import os

import pytest

# Required before Settings() is first constructed in tests.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5433/vivecaribe",
)
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-not-for-production")
os.environ.setdefault("CRON_SECRET", "test-cron-secret-not-for-production")
os.environ.setdefault("ENVIRONMENT", "local")
os.environ.setdefault("SENTRY_DSN", "")


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    """Reset ``get_settings`` cache so each test sees a fresh Settings instance."""
    from vivecaribe.settings import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()

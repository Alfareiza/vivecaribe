"""Engine / pooler connect-arg helpers."""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.pool import NullPool, QueuePool

from vivecaribe.infrastructure.db.session import (
    create_engine,
    pooler_connect_args,
    validate_async_database_url,
)
from vivecaribe.settings import Settings


def test_validate_async_database_url_accepts_asyncpg_and_psycopg() -> None:
    """Supported async drivers pass validation."""
    validate_async_database_url("postgresql+asyncpg://u:p@host:6543/postgres")
    validate_async_database_url("postgresql+psycopg://u:p@host:6543/postgres")


def test_validate_async_database_url_rejects_plain_postgresql() -> None:
    """Plain postgresql:// would load psycopg2, which we do not install."""
    with pytest.raises(ValueError, match="postgresql\\+asyncpg"):
        validate_async_database_url(
            "postgresql://postgres.ref:secret@host.pooler.supabase.com:6543/postgres",
        )


def test_validate_async_database_url_rejects_empty() -> None:
    """Empty DATABASE_URL gets an actionable startup error."""
    with pytest.raises(ValueError, match="DATABASE_URL is empty"):
        validate_async_database_url("")


def test_pooler_connect_args_asyncpg() -> None:
    """asyncpg disables its statement cache for transaction poolers."""
    assert pooler_connect_args(
        "postgresql+asyncpg://u:p@host:6543/postgres",
    ) == {"statement_cache_size": 0}


def test_pooler_connect_args_psycopg() -> None:
    """psycopg disables prepared statements via prepare_threshold."""
    assert pooler_connect_args(
        "postgresql+psycopg://u:p@host:6543/postgres",
    ) == {"prepare_threshold": None}


def test_local_engine_uses_queue_pool_without_pooler_args() -> None:
    """Local keeps a small QueuePool and does not force pooler connect args."""
    settings = Settings(
        environment="local",
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5433/vivecaribe",
        jwt_secret="secret",
        cron_secret="cron",
    )
    with patch(
        "vivecaribe.infrastructure.db.session.create_async_engine",
        return_value=MagicMock(),
    ) as mock_create:
        create_engine(settings)

    kwargs = mock_create.call_args.kwargs
    assert kwargs["pool_size"] == 5
    assert kwargs["max_overflow"] == 5
    assert "connect_args" not in kwargs
    assert "poolclass" not in kwargs


def test_staging_engine_uses_null_pool_and_psycopg_args() -> None:
    """Non-local + psycopg URL uses NullPool and prepare_threshold=None."""
    settings = Settings(
        environment="staging",
        database_url="postgresql+psycopg://u:p@host:6543/postgres",
        jwt_secret="secret",
        cron_secret="cron",
    )
    with patch(
        "vivecaribe.infrastructure.db.session.create_async_engine",
        return_value=MagicMock(),
    ) as mock_create:
        create_engine(settings)

    kwargs = mock_create.call_args.kwargs
    assert kwargs["poolclass"] is NullPool
    assert kwargs["connect_args"] == {"prepare_threshold": None}


def test_staging_engine_uses_asyncpg_statement_cache_arg() -> None:
    """Non-local + asyncpg URL still disables statement_cache_size."""
    settings = Settings(
        environment="staging",
        database_url="postgresql+asyncpg://u:p@host:6543/postgres",
        jwt_secret="secret",
        cron_secret="cron",
    )
    with patch(
        "vivecaribe.infrastructure.db.session.create_async_engine",
        return_value=MagicMock(),
    ) as mock_create:
        create_engine(settings)

    kwargs = mock_create.call_args.kwargs
    assert kwargs["poolclass"] is NullPool
    assert kwargs["connect_args"] == {"statement_cache_size": 0}


def test_local_engine_builds_real_queue_pool() -> None:
    """Smoke-check a real local engine still gets QueuePool sizing."""
    settings = Settings(
        environment="local",
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5433/vivecaribe",
        jwt_secret="secret",
        cron_secret="cron",
    )
    engine = create_engine(settings)
    assert isinstance(engine.sync_engine.pool, QueuePool)
    assert engine.sync_engine.pool.size() == 5

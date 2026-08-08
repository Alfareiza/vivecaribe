"""Async SQLAlchemy engine and session factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from vivecaribe.settings import Settings, get_settings

_ASYNC_DATABASE_DRIVERS = frozenset({"postgresql+asyncpg", "postgresql+psycopg"})


def validate_async_database_url(database_url: str) -> None:
    """Reject ``DATABASE_URL`` values that cannot work with ``create_async_engine``.

    Supabase dashboard URIs often use plain ``postgresql://``, which SQLAlchemy
    maps to sync ``psycopg2`` (not installed here). Require an async driver prefix
    so startup fails with an actionable message instead of ``ModuleNotFoundError``.
    """
    if not database_url.strip():
        msg = "DATABASE_URL is empty. Set it in Vercel (Production) or your local .env."
        raise ValueError(msg)

    try:
        driver = make_url(database_url).drivername
    except Exception as exc:
        msg = (
            "DATABASE_URL is not a valid SQLAlchemy URL. "
            "If the password contains @, #, or /, URL-encode it first."
        )
        raise ValueError(msg) from exc

    if driver in _ASYNC_DATABASE_DRIVERS:
        return

    if driver in {"postgresql", "postgres"} or driver.endswith("+psycopg2"):
        msg = (
            "DATABASE_URL must use an async driver: postgresql+asyncpg:// or "
            "postgresql+psycopg://. Plain postgresql:// selects psycopg2, "
            "which is not installed."
        )
        raise ValueError(msg)

    msg = (
        f"DATABASE_URL driver {driver!r} is not supported. "
        "Use postgresql+asyncpg:// or postgresql+psycopg://."
    )
    raise ValueError(msg)


def pooler_connect_args(database_url: str) -> dict[str, Any]:
    """Return driver-specific args that disable prepared statements.

    Required for Supabase / PgBouncer **transaction** poolers. ``asyncpg`` and
    ``psycopg`` use different option names; passing the wrong one fails at
    connect time.
    """
    driver = make_url(database_url).drivername
    if driver.endswith("+asyncpg"):
        return {"statement_cache_size": 0}
    if driver.endswith("+psycopg") or driver.endswith("+psycopg2"):
        return {"prepare_threshold": None}
    return {}


def create_engine(settings: Settings | None = None) -> AsyncEngine:
    """Build an async engine for the current environment.

    Local Docker Postgres uses a small pool with no special connect args.
    Staging/prod on Vercel should use Supabase **transaction** pooler (port
    ``6543``) with ``NullPool`` and prepared statements disabled for whichever
    async driver is in ``DATABASE_URL``.
    """
    settings = settings or get_settings()
    url = settings.database_url.get_secret_value()
    validate_async_database_url(url)
    is_local = settings.environment == "local"

    if is_local:
        return create_async_engine(
            url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
        )

    return create_async_engine(
        url,
        poolclass=NullPool,
        connect_args=pooler_connect_args(url),
    )


def create_session_factory(
    engine: AsyncEngine | None = None,
) -> async_sessionmaker[AsyncSession]:
    """Return an ``async_sessionmaker`` bound to ``engine``."""
    return async_sessionmaker(
        bind=engine or create_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Yield a session and commit on success / rollback on error."""
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

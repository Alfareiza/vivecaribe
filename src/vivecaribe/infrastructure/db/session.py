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

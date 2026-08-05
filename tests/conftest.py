"""Shared pytest fixtures."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from urllib.parse import urlparse, urlunparse

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

# Tests must never touch the local/dev database. Always force a ``*_test`` URL
# (override ``TEST_DATABASE_URL`` if you need a different host/port).
_DEFAULT_TEST_DATABASE_URL = (
    "postgresql+asyncpg://postgres:postgres@localhost:5433/vivecaribe_test"
)
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    _DEFAULT_TEST_DATABASE_URL,
)
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-not-for-production")
os.environ.setdefault("CRON_SECRET", "test-cron-secret-not-for-production")
os.environ.setdefault("ENVIRONMENT", "local")
os.environ.setdefault("SENTRY_DSN", "")


def _database_name(database_url: str) -> str:
    """Return the Postgres database name from a SQLAlchemy URL."""
    normalized = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    normalized = normalized.replace("postgresql+psycopg://", "postgresql://", 1)
    path = urlparse(normalized).path.lstrip("/")
    return path.split("?")[0]


def _to_asyncpg_dsn(database_url: str, *, database: str) -> str:
    """Build an ``asyncpg`` DSN for ``database`` from a SQLAlchemy URL."""
    normalized = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    normalized = normalized.replace("postgresql+psycopg://", "postgresql://", 1)
    parts = urlparse(normalized)
    return urlunparse(parts._replace(path=f"/{database}"))


def assert_is_test_database(database_url: str) -> None:
    """Refuse destructive fixtures unless the DB name ends with ``_test``."""
    name = _database_name(database_url)
    if not name.endswith("_test"):
        msg = (
            f"Refusing to reset database {name!r}. "
            "Integration tests must use a DATABASE_URL / TEST_DATABASE_URL "
            "whose name ends with '_test' (e.g. vivecaribe_test)."
        )
        raise RuntimeError(msg)


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    """Reset ``get_settings`` cache so each test sees a fresh Settings instance."""
    from vivecaribe.settings import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def postgres_available(engine: AsyncEngine) -> bool:
    """Return ``True`` if the engine can connect to Postgres."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def ensure_test_database() -> None:
    """Create the isolated ``*_test`` database when the test session starts.

    Connects to the server's ``postgres`` maintenance DB so tests do not
    depend on Docker init scripts or a pre-created database.
    """
    import asyncio

    import asyncpg

    database_url = os.environ["DATABASE_URL"]
    assert_is_test_database(database_url)
    db_name = _database_name(database_url)
    admin_dsn = _to_asyncpg_dsn(database_url, database="postgres")

    async def _create() -> None:
        try:
            conn = await asyncpg.connect(admin_dsn)
        except Exception as exc:
            pytest.skip(f"Postgres is not available for tests: {exc}")

        try:
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1",
                db_name,
            )
            if not exists:
                # CREATE DATABASE cannot run inside a transaction block.
                await conn.execute(f'CREATE DATABASE "{db_name}"')
        finally:
            await conn.close()

    asyncio.run(_create())


@pytest.fixture
async def db_engine(ensure_test_database: None) -> AsyncIterator[AsyncEngine]:
    """Async engine bound to the isolated test database (schema reset per test)."""
    from vivecaribe.infrastructure.db.models import Base
    from vivecaribe.infrastructure.db.session import create_engine
    from vivecaribe.settings import get_settings

    settings = get_settings()
    assert_is_test_database(settings.database_url.get_secret_value())

    eng = create_engine(settings)
    if not await postgres_available(eng):
        await eng.dispose()
        pytest.skip("Test Postgres is not available (start with: docker compose up -d db)")

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield eng

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Yield a session bound to the isolated test engine."""
    factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with factory() as session:
        yield session
        await session.commit()


@pytest.fixture
def settings():
    """Return a fresh ``Settings`` instance for the current env."""
    from vivecaribe.settings import get_settings

    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
async def auth_client(db_engine: AsyncEngine) -> AsyncIterator[AsyncClient]:
    """HTTP client against the app using the isolated test database."""
    from vivecaribe.api import deps
    from vivecaribe.main import create_app

    factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app = create_app()
    app.dependency_overrides[deps.get_db_session] = override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


async def auth_headers(
    client: AsyncClient,
    *,
    email: str = "ops@vivecaribe.com",
    password: str = "secret123",
) -> dict[str, str]:
    """Register + login and return an Authorization bearer header dict."""
    await client.post("/users", json={"email": email, "password": password})
    login = await client.post("/login", json={"email": email, "password": password})
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

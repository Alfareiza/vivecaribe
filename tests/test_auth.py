"""API tests for register and login."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from vivecaribe.api import deps
from vivecaribe.main import create_app


@pytest.fixture
async def auth_client(db_engine: AsyncEngine) -> AsyncIterator[AsyncClient]:
    """HTTP client against the app using the isolated test database."""
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


@pytest.mark.asyncio
async def test_register_and_login_happy_path(auth_client: AsyncClient) -> None:
    """Register returns 201 without hash; login returns a bearer token."""
    register = await auth_client.post(
        "/users",
        json={"email": "ops@vivecaribe.com", "password": "secret123"},
    )
    assert register.status_code == 201
    body = register.json()
    assert body["email"] == "ops@vivecaribe.com"
    assert "password_hash" not in body
    assert body["is_active"] is True

    login = await auth_client.post(
        "/login",
        json={"email": "ops@vivecaribe.com", "password": "secret123"},
    )
    assert login.status_code == 200
    token_body = login.json()
    assert token_body["token_type"] == "bearer"
    assert token_body["access_token"]


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(auth_client: AsyncClient) -> None:
    """Duplicate registration yields a simple 409 conflict."""
    payload = {"email": "dup@vivecaribe.com", "password": "secret123"}
    first = await auth_client.post("/users", json=payload)
    second = await auth_client.post("/users", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
    assert "already" in second.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_bad_password_returns_401(auth_client: AsyncClient) -> None:
    """Wrong password returns 401 without leaking which field failed."""
    await auth_client.post(
        "/users",
        json={"email": "bad@vivecaribe.com", "password": "secret123"},
    )
    response = await auth_client.post(
        "/login",
        json={"email": "bad@vivecaribe.com", "password": "wrong-pass"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_register_short_password_returns_422(auth_client: AsyncClient) -> None:
    """Passwords shorter than 8 characters are rejected by the schema."""
    response = await auth_client.post(
        "/users",
        json={"email": "short@vivecaribe.com", "password": "1234567"},
    )
    assert response.status_code == 422

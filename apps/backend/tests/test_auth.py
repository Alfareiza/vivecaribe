"""API tests for register, login, refresh, and logout."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from vivecaribe.api.cookies import REFRESH_COOKIE_NAME


@pytest.mark.asyncio
async def test_register_and_login_happy_path(auth_client: AsyncClient) -> None:
    """Register returns 201 without hash; login returns bearer + refresh cookie."""
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
    assert "refresh_token" not in token_body
    assert REFRESH_COOKIE_NAME in login.cookies


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


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401(auth_client: AsyncClient) -> None:
    """Unknown email returns the same 401 as a bad password."""
    response = await auth_client.post(
        "/login",
        json={"email": "missing@vivecaribe.com", "password": "secret123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_inactive_user_returns_401(
    auth_client: AsyncClient,
    db_session,
) -> None:
    """Inactive users cannot obtain a JWT."""
    from vivecaribe.domain.user import User
    from vivecaribe.infrastructure.db.repositories import SqlAlchemyUserRepository
    from vivecaribe.infrastructure.integrations.security import Argon2PasswordHasher

    hasher = Argon2PasswordHasher()
    repo = SqlAlchemyUserRepository(db_session)
    await repo.save(
        User(
            email="inactive@vivecaribe.com",
            password_hash=hasher.hash("secret123"),
            is_active=False,
        ),
    )
    await db_session.commit()

    response = await auth_client.post(
        "/login",
        json={"email": "inactive@vivecaribe.com", "password": "secret123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_returns_new_access_and_rotates_cookie(
    auth_client: AsyncClient,
) -> None:
    """``POST /refresh`` mints a new access token and rotates the cookie."""
    await auth_client.post(
        "/users",
        json={"email": "refresh@vivecaribe.com", "password": "secret123"},
    )
    login = await auth_client.post(
        "/login",
        json={"email": "refresh@vivecaribe.com", "password": "secret123"},
    )
    assert login.status_code == 200
    old_cookie = login.cookies[REFRESH_COOKIE_NAME]
    old_access = login.json()["access_token"]

    refreshed = await auth_client.post("/refresh")
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]
    assert refreshed.json()["access_token"] != old_access
    assert "refresh_token" not in refreshed.json()
    new_cookie = refreshed.cookies.get(REFRESH_COOKIE_NAME)
    assert new_cookie
    assert new_cookie != old_cookie


@pytest.mark.asyncio
async def test_refresh_without_cookie_returns_401(auth_client: AsyncClient) -> None:
    """Missing refresh cookie yields 401."""
    response = await auth_client.post("/refresh")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_reuse_of_rotated_cookie_returns_401(
    auth_client: AsyncClient,
) -> None:
    """Presenting a rotated refresh cookie fails and revokes the family."""
    await auth_client.post(
        "/users",
        json={"email": "reuse@vivecaribe.com", "password": "secret123"},
    )
    login = await auth_client.post(
        "/login",
        json={"email": "reuse@vivecaribe.com", "password": "secret123"},
    )
    old_cookie = login.cookies[REFRESH_COOKIE_NAME]

    first = await auth_client.post("/refresh")
    assert first.status_code == 200
    current_cookie = first.cookies[REFRESH_COOKIE_NAME]

    # Force the jar back to the rotated (old) cookie.
    auth_client.cookies.set(REFRESH_COOKIE_NAME, old_cookie)
    reuse = await auth_client.post("/refresh")
    assert reuse.status_code == 401

    auth_client.cookies.set(REFRESH_COOKIE_NAME, current_cookie)
    after_reuse = await auth_client.post("/refresh")
    assert after_reuse.status_code == 401


@pytest.mark.asyncio
async def test_logout_clears_cookie_and_blocks_refresh(
    auth_client: AsyncClient,
) -> None:
    """``POST /logout`` clears the cookie and revokes the refresh family."""
    await auth_client.post(
        "/users",
        json={"email": "logout@vivecaribe.com", "password": "secret123"},
    )
    login = await auth_client.post(
        "/login",
        json={"email": "logout@vivecaribe.com", "password": "secret123"},
    )
    cookie = login.cookies[REFRESH_COOKIE_NAME]

    logout = await auth_client.post("/logout")
    assert logout.status_code == 204

    auth_client.cookies.set(REFRESH_COOKIE_NAME, cookie)
    refreshed = await auth_client.post("/refresh")
    assert refreshed.status_code == 401

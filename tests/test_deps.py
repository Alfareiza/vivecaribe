"""FastAPI dependency unit tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from vivecaribe.api import deps
from vivecaribe.domain.errors import DomainError
from vivecaribe.domain.user import User
from vivecaribe.settings import get_settings


@pytest.mark.asyncio
async def test_init_db_and_shutdown_db(monkeypatch: pytest.MonkeyPatch) -> None:
    """Process-wide engine is created and disposed."""
    fake_engine = MagicMock()
    fake_engine.dispose = AsyncMock()
    monkeypatch.setattr(deps, "create_engine", lambda: fake_engine)
    monkeypatch.setattr(
        deps,
        "create_session_factory",
        lambda engine: MagicMock(),
    )
    deps._engine = None
    deps._session_factory = None

    engine = deps.init_db()
    assert engine is fake_engine
    assert deps._session_factory is not None

    await deps.shutdown_db()
    fake_engine.dispose.assert_awaited_once()
    assert deps._engine is None
    assert deps._session_factory is None


@pytest.mark.asyncio
async def test_get_db_session_commits_and_rolls_back() -> None:
    """Successful sessions commit; failures roll back."""
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    class _CM:
        async def __aenter__(self) -> MagicMock:
            return session

        async def __aexit__(self, *args: object) -> None:
            return None

    factory = MagicMock(return_value=_CM())
    deps._session_factory = factory

    gen = deps.get_db_session()
    yielded = await gen.__anext__()
    assert yielded is session
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()
    session.commit.assert_awaited()

    session.commit.reset_mock()
    session.rollback.reset_mock()
    gen = deps.get_db_session()
    await gen.__anext__()
    with pytest.raises(RuntimeError):
        await gen.athrow(RuntimeError("boom"))
    session.rollback.assert_awaited()


@pytest.mark.asyncio
async def test_get_current_user_missing_credentials() -> None:
    """No Bearer credentials ⇒ 401 Not authenticated."""
    with pytest.raises(HTTPException) as exc:
        await deps.get_current_user(
            None,
            users=MagicMock(),
            tokens=MagicMock(),
        )
    assert exc.value.status_code == 401
    assert exc.value.detail == "Not authenticated"


@pytest.mark.asyncio
async def test_get_current_user_non_bearer_scheme() -> None:
    """Non-bearer schemes are rejected."""
    creds = HTTPAuthorizationCredentials(scheme="Basic", credentials="x")
    with pytest.raises(HTTPException) as exc:
        await deps.get_current_user(creds, users=MagicMock(), tokens=MagicMock())
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_invalid_token() -> None:
    """Token decode failures map to 401."""
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad")
    tokens = MagicMock()
    tokens.decode_access_token.side_effect = DomainError("bad")
    with pytest.raises(HTTPException) as exc:
        await deps.get_current_user(creds, users=MagicMock(), tokens=tokens)
    assert exc.value.detail == "Invalid or expired token"


@pytest.mark.asyncio
async def test_get_current_user_missing_or_inactive() -> None:
    """Missing or inactive users map to 401."""
    user_id = uuid4()
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="tok")
    tokens = MagicMock()
    tokens.decode_access_token.return_value = str(user_id)
    users = MagicMock()
    users.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(HTTPException):
        await deps.get_current_user(creds, users=users, tokens=tokens)

    inactive = User(
        id=user_id,
        email="x@y.com",
        password_hash="h",
        is_active=False,
    )
    users.get_by_id = AsyncMock(return_value=inactive)
    with pytest.raises(HTTPException):
        await deps.get_current_user(creds, users=users, tokens=tokens)


@pytest.mark.asyncio
async def test_get_current_user_happy_path() -> None:
    """Valid token + active user returns the user."""
    user = User(id=uuid4(), email="ops@vivecaribe.com", password_hash="h")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="tok")
    tokens = MagicMock()
    tokens.decode_access_token.return_value = str(user.id)
    users = MagicMock()
    users.get_by_id = AsyncMock(return_value=user)
    found = await deps.get_current_user(creds, users=users, tokens=tokens)
    assert found.id == user.id


def test_get_process_booking_emails_use_case_wiring(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Factory wires YAML accounts, repos, and NoOp WhatsApp."""
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("JWT_SECRET", "secret")
    monkeypatch.setenv("CRON_SECRET", "cron")
    session = MagicMock()
    use_case = deps.get_process_booking_emails_use_case(session)
    assert use_case._whatsapp.__class__.__name__ == "NoOpWhatsAppNotifier"
    assert use_case._accounts
    get_settings.cache_clear()


def test_password_hasher_and_token_service_singletons() -> None:
    """Shared hasher/token helpers return the process singletons."""
    assert deps.get_password_hasher() is deps._password_hasher
    assert deps.get_token_service() is deps._token_service


@pytest.mark.asyncio
async def test_require_jwt_or_cron_missing_credentials() -> None:
    """No Bearer credentials ⇒ 401."""
    with pytest.raises(HTTPException) as exc:
        await deps.require_jwt_or_cron(
            None,
            users=MagicMock(),
            tokens=MagicMock(),
        )
    assert exc.value.status_code == 401
    assert exc.value.detail == "Not authenticated"


@pytest.mark.asyncio
async def test_require_jwt_or_cron_accepts_cron_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bearer matching CRON_SECRET returns None (no user)."""
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("JWT_SECRET", "secret")
    monkeypatch.setenv("CRON_SECRET", "cron-secret-value")
    get_settings.cache_clear()

    creds = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="cron-secret-value",
    )
    result = await deps.require_jwt_or_cron(
        creds,
        users=MagicMock(),
        tokens=MagicMock(),
    )
    assert result is None
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_require_jwt_or_cron_rejects_wrong_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wrong Bearer that is not a JWT returns 401."""
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("JWT_SECRET", "secret")
    monkeypatch.setenv("CRON_SECRET", "cron-secret-value")
    get_settings.cache_clear()

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong")
    tokens = MagicMock()
    tokens.decode_access_token.side_effect = DomainError("bad")
    with pytest.raises(HTTPException) as exc:
        await deps.require_jwt_or_cron(creds, users=MagicMock(), tokens=tokens)
    assert exc.value.status_code == 401
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_require_jwt_or_cron_falls_back_to_jwt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid JWT still authenticates when Bearer is not the cron secret."""
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("JWT_SECRET", "secret")
    monkeypatch.setenv("CRON_SECRET", "cron-secret-value")
    get_settings.cache_clear()

    user = User(id=uuid4(), email="ops@vivecaribe.com", password_hash="h")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="jwt-tok")
    tokens = MagicMock()
    tokens.decode_access_token.return_value = str(user.id)
    users = MagicMock()
    users.get_by_id = AsyncMock(return_value=user)

    found = await deps.require_jwt_or_cron(creds, users=users, tokens=tokens)
    assert found is not None
    assert found.id == user.id
    get_settings.cache_clear()

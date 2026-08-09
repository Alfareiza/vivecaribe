"""Auth use-case unit tests with in-memory fakes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from vivecaribe.application.auth.use_cases import (
    LoginUserUseCase,
    LogoutUserUseCase,
    RefreshAccessTokenUseCase,
    RegisterUserUseCase,
)
from vivecaribe.domain.errors import ConflictError, DomainError
from vivecaribe.domain.refresh_token import RefreshToken
from vivecaribe.domain.user import User
from vivecaribe.infrastructure.integrations.security import JwtTokenService


class FakeUsers:
    """Minimal user store for auth use-case tests."""

    def __init__(self) -> None:
        self.by_email: dict[str, User] = {}
        self.by_id: dict[UUID, User] = {}

    async def get_by_email(self, email: str) -> User | None:
        return self.by_email.get(email)

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self.by_id.get(user_id)

    async def save(self, user: User) -> User:
        self.by_email[str(user.email)] = user
        self.by_id[user.id] = user
        return user


class FakeHasher:
    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == f"hashed:{password}"


class FakeTokens:
    def create_access_token(self, *, subject: str, email: str) -> str:
        return f"token:{subject}:{email}"

    def generate_refresh_token(self) -> str:
        return f"refresh-{uuid4()}"

    def hash_refresh_token(self, raw_token: str) -> str:
        return f"hash:{raw_token}"


class FakeRefreshTokens:
    def __init__(self) -> None:
        self.by_hash: dict[str, RefreshToken] = {}
        self.by_id: dict[UUID, RefreshToken] = {}

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        return self.by_hash.get(token_hash)

    async def save(self, token: RefreshToken) -> RefreshToken:
        self.by_hash[token.token_hash] = token
        self.by_id[token.id] = token
        return token

    async def revoke(
        self,
        token_id: UUID,
        *,
        replaced_by_id: UUID | None = None,
        revoked_at: datetime | None = None,
    ) -> None:
        token = self.by_id[token_id]
        token.revoked_at = revoked_at or datetime.now(UTC)
        if replaced_by_id is not None:
            token.replaced_by_id = replaced_by_id

    async def revoke_family(
        self,
        family_id: UUID,
        *,
        revoked_at: datetime | None = None,
    ) -> int:
        when = revoked_at or datetime.now(UTC)
        count = 0
        for token in self.by_id.values():
            if token.family_id == family_id and token.revoked_at is None:
                token.revoked_at = when
                count += 1
        return count


def _login_use_case(
    users: FakeUsers,
    refresh: FakeRefreshTokens | None = None,
) -> tuple[LoginUserUseCase, FakeRefreshTokens]:
    store = refresh or FakeRefreshTokens()
    return (
        LoginUserUseCase(
            users,
            FakeHasher(),
            FakeTokens(),
            store,
            refresh_expire_days=7,
        ),
        store,
    )


@pytest.mark.asyncio
async def test_register_happy_path() -> None:
    users = FakeUsers()
    use_case = RegisterUserUseCase(users, FakeHasher())
    user = await use_case.execute(email="ops@vivecaribe.com", password="secret123")
    assert user.email == "ops@vivecaribe.com"
    assert user.password_hash == "hashed:secret123"


@pytest.mark.asyncio
async def test_register_duplicate_raises_conflict() -> None:
    users = FakeUsers()
    users.by_email["ops@vivecaribe.com"] = User(
        id=uuid4(),
        email="ops@vivecaribe.com",
        password_hash="x",
    )
    use_case = RegisterUserUseCase(users, FakeHasher())
    with pytest.raises(ConflictError):
        await use_case.execute(email="ops@vivecaribe.com", password="secret123")


@pytest.mark.asyncio
async def test_login_happy_path() -> None:
    users = FakeUsers()
    user = User(
        id=uuid4(),
        email="ops@vivecaribe.com",
        password_hash="hashed:secret123",
    )
    await users.save(user)
    use_case, store = _login_use_case(users)
    pair = await use_case.execute(email="ops@vivecaribe.com", password="secret123")
    assert pair.access_token.startswith("token:")
    assert pair.refresh_token
    assert len(store.by_hash) == 1


@pytest.mark.asyncio
async def test_login_unknown_email_raises() -> None:
    use_case, _ = _login_use_case(FakeUsers())
    with pytest.raises(DomainError, match="Invalid"):
        await use_case.execute(email="missing@vivecaribe.com", password="secret123")


@pytest.mark.asyncio
async def test_login_inactive_user_raises() -> None:
    users = FakeUsers()
    await users.save(
        User(
            id=uuid4(),
            email="ops@vivecaribe.com",
            password_hash="hashed:secret123",
            is_active=False,
        ),
    )
    use_case, _ = _login_use_case(users)
    with pytest.raises(DomainError, match="Invalid"):
        await use_case.execute(email="ops@vivecaribe.com", password="secret123")


@pytest.mark.asyncio
async def test_refresh_rotates_and_revokes_old() -> None:
    users = FakeUsers()
    user = User(
        id=uuid4(),
        email="ops@vivecaribe.com",
        password_hash="hashed:secret123",
    )
    await users.save(user)
    login, store = _login_use_case(users)
    pair = await login.execute(email="ops@vivecaribe.com", password="secret123")
    old_raw = pair.refresh_token

    refresh = RefreshAccessTokenUseCase(
        users,
        FakeTokens(),
        store,
        refresh_expire_days=7,
    )
    new_pair = await refresh.execute(raw_refresh_token=old_raw)
    assert new_pair.refresh_token != old_raw
    old = await store.get_by_token_hash(FakeTokens().hash_refresh_token(old_raw))
    assert old is not None
    assert old.is_revoked
    assert old.replaced_by_id is not None


@pytest.mark.asyncio
async def test_refresh_reuse_revokes_family() -> None:
    users = FakeUsers()
    user = User(
        id=uuid4(),
        email="ops@vivecaribe.com",
        password_hash="hashed:secret123",
    )
    await users.save(user)
    login, store = _login_use_case(users)
    pair = await login.execute(email="ops@vivecaribe.com", password="secret123")
    old_raw = pair.refresh_token

    refresh = RefreshAccessTokenUseCase(
        users,
        FakeTokens(),
        store,
        refresh_expire_days=7,
    )
    new_pair = await refresh.execute(raw_refresh_token=old_raw)

    with pytest.raises(DomainError, match="Invalid refresh"):
        await refresh.execute(raw_refresh_token=old_raw)

    current = await store.get_by_token_hash(
        FakeTokens().hash_refresh_token(new_pair.refresh_token),
    )
    assert current is not None
    assert current.is_revoked


@pytest.mark.asyncio
async def test_logout_revokes_family() -> None:
    users = FakeUsers()
    user = User(
        id=uuid4(),
        email="ops@vivecaribe.com",
        password_hash="hashed:secret123",
    )
    await users.save(user)
    login, store = _login_use_case(users)
    pair = await login.execute(email="ops@vivecaribe.com", password="secret123")

    await LogoutUserUseCase(FakeTokens(), store).execute(
        raw_refresh_token=pair.refresh_token,
    )
    stored = await store.get_by_token_hash(
        FakeTokens().hash_refresh_token(pair.refresh_token),
    )
    assert stored is not None
    assert stored.is_revoked


def test_hash_refresh_token_is_sha256() -> None:
    """Opaque refresh hashing matches SHA-256 hex digest."""
    raw = "example-refresh-token"
    assert len(JwtTokenService.hash_refresh_token(raw)) == 64
    assert JwtTokenService.hash_refresh_token(raw) == JwtTokenService.hash_refresh_token(
        raw,
    )


@pytest.mark.asyncio
async def test_refresh_expired_token_raises() -> None:
    users = FakeUsers()
    user = User(
        id=uuid4(),
        email="ops@vivecaribe.com",
        password_hash="hashed:secret123",
    )
    await users.save(user)
    store = FakeRefreshTokens()
    tokens = FakeTokens()
    raw = tokens.generate_refresh_token()
    await store.save(
        RefreshToken(
            user_id=user.id,
            family_id=uuid4(),
            token_hash=tokens.hash_refresh_token(raw),
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        ),
    )
    refresh = RefreshAccessTokenUseCase(
        users,
        tokens,
        store,
        refresh_expire_days=7,
    )
    with pytest.raises(DomainError, match="Invalid refresh"):
        await refresh.execute(raw_refresh_token=raw)

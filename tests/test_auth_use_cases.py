"""Auth use-case unit tests with in-memory fakes."""

from __future__ import annotations

from uuid import uuid4

import pytest

from vivecaribe.application.auth.use_cases import LoginUserUseCase, RegisterUserUseCase
from vivecaribe.domain.errors import ConflictError, DomainError
from vivecaribe.domain.user import User


class FakeUsers:
    """Minimal user store for auth use-case tests."""

    def __init__(self) -> None:
        self.by_email: dict[str, User] = {}

    async def get_by_email(self, email: str) -> User | None:
        return self.by_email.get(email)

    async def save(self, user: User) -> User:
        self.by_email[str(user.email)] = user
        return user


class FakeHasher:
    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == f"hashed:{password}"


class FakeTokens:
    def create_access_token(self, *, subject: str, email: str) -> str:
        return f"token:{subject}:{email}"


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
    users.by_email[str(user.email)] = user
    use_case = LoginUserUseCase(users, FakeHasher(), FakeTokens())
    token = await use_case.execute(email="ops@vivecaribe.com", password="secret123")
    assert token.startswith("token:")


@pytest.mark.asyncio
async def test_login_unknown_email_raises() -> None:
    use_case = LoginUserUseCase(FakeUsers(), FakeHasher(), FakeTokens())
    with pytest.raises(DomainError, match="Invalid"):
        await use_case.execute(email="missing@vivecaribe.com", password="secret123")


@pytest.mark.asyncio
async def test_login_inactive_user_raises() -> None:
    users = FakeUsers()
    users.by_email["ops@vivecaribe.com"] = User(
        id=uuid4(),
        email="ops@vivecaribe.com",
        password_hash="hashed:secret123",
        is_active=False,
    )
    use_case = LoginUserUseCase(users, FakeHasher(), FakeTokens())
    with pytest.raises(DomainError, match="Invalid"):
        await use_case.execute(email="ops@vivecaribe.com", password="secret123")

"""Register and login use cases."""

from __future__ import annotations

from vivecaribe.domain.errors import ConflictError, DomainError
from vivecaribe.domain.ports import PasswordHasher, TokenService, UserRepository
from vivecaribe.domain.user import User
from vivecaribe.logging import logger


class RegisterUserUseCase:
    """Create a new platform user with a hashed password."""

    def __init__(
        self,
        users: UserRepository,
        password_hasher: PasswordHasher,
    ) -> None:
        """Wire persistence and hashing adapters."""
        self._users = users
        self._password_hasher = password_hasher

    async def execute(self, *, email: str, password: str) -> User:
        """Register a user or raise if the email is already taken.

        Raises:
            ConflictError: When ``email`` already exists.
        """
        existing = await self._users.get_by_email(email)
        if existing is not None:
            raise ConflictError("Email already registered")

        user = User(
            email=email,
            password_hash=self._password_hasher.hash(password),
        )
        saved = await self._users.save(user)
        logger.info("Registered user %s", saved.id)
        return saved


class LoginUserUseCase:
    """Authenticate a user and issue a JWT access token."""

    def __init__(
        self,
        users: UserRepository,
        password_hasher: PasswordHasher,
        tokens: TokenService,
    ) -> None:
        """Wire persistence, hashing, and token adapters."""
        self._users = users
        self._password_hasher = password_hasher
        self._tokens = tokens

    async def execute(self, *, email: str, password: str) -> str:
        """Verify credentials and return a JWT.

        Raises:
            DomainError: When credentials are invalid or the user is inactive.
        """
        user = await self._users.get_by_email(email)
        if user is None or not self._password_hasher.verify(
            password,
            user.password_hash,
        ):
            raise DomainError("Invalid email or password")
        if not user.is_active:
            raise DomainError("Invalid email or password")

        return self._tokens.create_access_token(
            subject=str(user.id),
            email=str(user.email),
        )

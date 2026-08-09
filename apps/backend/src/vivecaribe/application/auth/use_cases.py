"""Register, login, refresh, and logout use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from vivecaribe.domain.errors import ConflictError, DomainError
from vivecaribe.domain.refresh_token import RefreshToken
from vivecaribe.domain.user import User
from vivecaribe.logging import logger


@dataclass(frozen=True, slots=True)
class AuthTokenPair:
    """Access JWT plus raw refresh token (cookie value; never persist raw)."""

    access_token: str
    refresh_token: str


class RegisterUserUseCase:
    """Create a new platform user with a hashed password."""

    def __init__(self, users: Any, password_hasher: Any) -> None:
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
        logger.info(f"Registered user {saved.id}")
        return saved


class LoginUserUseCase:
    """Authenticate a user and issue access + refresh credentials."""

    def __init__(
        self,
        users: Any,
        password_hasher: Any,
        tokens: Any,
        refresh_tokens: Any,
        *,
        refresh_expire_days: int,
    ) -> None:
        """Wire persistence, hashing, and token adapters."""
        self._users = users
        self._password_hasher = password_hasher
        self._tokens = tokens
        self._refresh_tokens = refresh_tokens
        self._refresh_expire_days = refresh_expire_days

    async def execute(self, *, email: str, password: str) -> AuthTokenPair:
        """Verify credentials and return access + refresh tokens.

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

        pair, _ = await _issue_token_pair(
            user=user,
            tokens=self._tokens,
            refresh_tokens=self._refresh_tokens,
            refresh_expire_days=self._refresh_expire_days,
            family_id=uuid4(),
        )
        return pair


class RefreshAccessTokenUseCase:
    """Rotate a refresh token and mint a new access JWT."""

    def __init__(
        self,
        users: Any,
        tokens: Any,
        refresh_tokens: Any,
        *,
        refresh_expire_days: int,
    ) -> None:
        """Wire user lookup and token adapters."""
        self._users = users
        self._tokens = tokens
        self._refresh_tokens = refresh_tokens
        self._refresh_expire_days = refresh_expire_days

    async def execute(self, *, raw_refresh_token: str) -> AuthTokenPair:
        """Validate the refresh cookie value and return a rotated pair.

        Raises:
            DomainError: When the token is missing, expired, revoked, or the
                user is inactive. Reuse of a rotated token revokes the family.
        """
        token_hash = self._tokens.hash_refresh_token(raw_refresh_token)
        existing = await self._refresh_tokens.get_by_token_hash(token_hash)
        if existing is None:
            raise DomainError("Invalid refresh token")

        if existing.is_revoked:
            if existing.replaced_by_id is not None:
                await self._refresh_tokens.revoke_family(existing.family_id)
                logger.warning(
                    f"Refresh token reuse detected; revoked family {existing.family_id}",
                )
            raise DomainError("Invalid refresh token")

        if existing.is_expired:
            await self._refresh_tokens.revoke(existing.id)
            raise DomainError("Invalid refresh token")

        user = await self._users.get_by_id(existing.user_id)
        if user is None or not user.is_active:
            await self._refresh_tokens.revoke_family(existing.family_id)
            raise DomainError("Invalid refresh token")

        pair, replacement = await _issue_token_pair(
            user=user,
            tokens=self._tokens,
            refresh_tokens=self._refresh_tokens,
            refresh_expire_days=self._refresh_expire_days,
            family_id=existing.family_id,
        )
        await self._refresh_tokens.revoke(
            existing.id,
            replaced_by_id=replacement.id,
        )
        return pair


class LogoutUserUseCase:
    """Revoke the refresh-token family for the presented cookie."""

    def __init__(self, tokens: Any, refresh_tokens: Any) -> None:
        """Wire hashing and refresh-token persistence."""
        self._tokens = tokens
        self._refresh_tokens = refresh_tokens

    async def execute(self, *, raw_refresh_token: str | None) -> None:
        """Revoke the token family when a valid cookie is present."""
        if not raw_refresh_token:
            return
        token_hash = self._tokens.hash_refresh_token(raw_refresh_token)
        existing = await self._refresh_tokens.get_by_token_hash(token_hash)
        if existing is None:
            return
        await self._refresh_tokens.revoke_family(existing.family_id)
        logger.info(f"Revoked refresh family {existing.family_id}")


async def _issue_token_pair(
    *,
    user: User,
    tokens: Any,
    refresh_tokens: Any,
    refresh_expire_days: int,
    family_id: Any,
) -> tuple[AuthTokenPair, RefreshToken]:
    """Persist a new refresh token and return access + raw refresh values."""
    access_token = tokens.create_access_token(
        subject=str(user.id),
        email=str(user.email),
    )
    raw_refresh = tokens.generate_refresh_token()
    entity = RefreshToken(
        user_id=user.id,
        family_id=family_id,
        token_hash=tokens.hash_refresh_token(raw_refresh),
        expires_at=datetime.now(UTC) + timedelta(days=refresh_expire_days),
    )
    saved = await refresh_tokens.save(entity)
    return (
        AuthTokenPair(access_token=access_token, refresh_token=raw_refresh),
        saved,
    )

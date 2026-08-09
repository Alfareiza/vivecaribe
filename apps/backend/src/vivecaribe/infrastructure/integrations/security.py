"""Argon2 password hashing, JWT access tokens, and opaque refresh tokens."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher as Argon2Hasher
from argon2.exceptions import VerifyMismatchError

from vivecaribe.domain.errors import DomainError, ValidationError
from vivecaribe.settings import Settings, get_settings


class Argon2PasswordHasher:
    """``PasswordHasher`` implementation using Argon2."""

    def __init__(self) -> None:
        """Create a hasher with Argon2 defaults."""
        self._hasher = Argon2Hasher()

    def hash(self, password: str) -> str:
        """Return a one-way Argon2 hash for ``password``."""
        return self._hasher.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        """Return ``True`` if ``password`` matches ``password_hash``."""
        try:
            return self._hasher.verify(password_hash, password)
        except VerifyMismatchError:
            return False


class JwtTokenService:
    """``TokenService`` implementation using HS256 JWTs."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Bind JWT secret and expiry from settings."""
        self._settings = settings or get_settings()

    def create_access_token(self, *, subject: str, email: str) -> str:
        """Create a signed access token with ``sub``, ``email``, ``jti``, and ``exp``."""
        expires = datetime.now(UTC) + timedelta(
            minutes=self._settings.jwt_expire_minutes,
        )
        payload = {
            "sub": subject,
            "email": email,
            "jti": secrets.token_urlsafe(16),
            "exp": expires,
        }
        return jwt.encode(
            payload,
            self._settings.jwt_secret.get_secret_value(),
            algorithm="HS256",
        )

    def decode_access_token(self, token: str) -> str:
        """Return the subject (user id) from a valid JWT.

        Raises:
            DomainError: If the token is invalid or expired.
        """
        try:
            payload = jwt.decode(
                token,
                self._settings.jwt_secret.get_secret_value(),
                algorithms=["HS256"],
            )
        except jwt.PyJWTError as exc:
            raise DomainError("Invalid or expired token") from exc

        subject = payload.get("sub")
        if not subject or not isinstance(subject, str):
            raise ValidationError("Token missing subject", field="sub")
        return subject

    @staticmethod
    def generate_refresh_token() -> str:
        """Return a new opaque refresh token (store only its hash)."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_refresh_token(raw_token: str) -> str:
        """Return the SHA-256 hex digest of ``raw_token``."""
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

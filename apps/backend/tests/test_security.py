"""Argon2 hasher and JWT token service unit tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from vivecaribe.domain.errors import DomainError, ValidationError
from vivecaribe.infrastructure.integrations.security import (
    Argon2PasswordHasher,
    JwtTokenService,
)
from vivecaribe.settings import Settings


def _settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        jwt_secret="unit-test-secret-at-least-32-bytes!!",
        cron_secret="cron",
        jwt_expire_minutes=60,
    )


def test_argon2_hash_and_verify_round_trip() -> None:
    """Matching passwords verify; mismatches return False."""
    hasher = Argon2PasswordHasher()
    hashed = hasher.hash("secret123")
    assert hasher.verify("secret123", hashed) is True
    assert hasher.verify("wrong", hashed) is False


def test_jwt_round_trip() -> None:
    """Issued tokens decode back to the subject user id."""
    service = JwtTokenService(_settings())
    subject = str(uuid4())
    token = service.create_access_token(subject=subject, email="ops@vivecaribe.com")
    assert service.decode_access_token(token) == subject


def test_jwt_decode_invalid_raises_domain_error() -> None:
    """Malformed tokens raise DomainError."""
    service = JwtTokenService(_settings())
    with pytest.raises(DomainError, match="Invalid or expired"):
        service.decode_access_token("not.a.jwt")


def test_jwt_decode_missing_sub_raises_validation_error() -> None:
    """Tokens without a string ``sub`` raise ValidationError."""
    settings = _settings()
    token = jwt.encode(
        {
            "email": "ops@vivecaribe.com",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )
    service = JwtTokenService(settings)
    with pytest.raises(ValidationError, match="subject"):
        service.decode_access_token(token)


def test_generate_and_hash_refresh_token() -> None:
    """Opaque refresh tokens are unique and hash stably to 64 hex chars."""
    first = JwtTokenService.generate_refresh_token()
    second = JwtTokenService.generate_refresh_token()
    assert first != second
    digest = JwtTokenService.hash_refresh_token(first)
    assert len(digest) == 64
    assert digest == JwtTokenService.hash_refresh_token(first)

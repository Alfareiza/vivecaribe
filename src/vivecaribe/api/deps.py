"""FastAPI dependencies — DB session, auth adapters, JWT guard."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from vivecaribe.application.automation.use_cases import ProcessBookingEmailsUseCase
from vivecaribe.domain.errors import DomainError
from vivecaribe.domain.user import User
from vivecaribe.infrastructure.db.repositories import (
    SqlAlchemyEmailMessageRepository,
    SqlAlchemyReservaRepository,
    SqlAlchemyUserRepository,
)
from vivecaribe.infrastructure.db.session import create_engine, create_session_factory
from vivecaribe.infrastructure.integrations.security import (
    Argon2PasswordHasher,
    JwtTokenService,
)
from vivecaribe.infrastructure.integrations.whatsapp import NoOpWhatsAppNotifier
from vivecaribe.settings import get_settings

_bearer = HTTPBearer(auto_error=False)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_password_hasher = Argon2PasswordHasher()
_token_service = JwtTokenService()


def init_db() -> AsyncEngine:
    """Create the process-wide async engine and session factory."""
    global _engine, _session_factory
    _engine = create_engine()
    _session_factory = create_session_factory(_engine)
    return _engine


async def shutdown_db() -> None:
    """Dispose the process-wide engine."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped DB session (commit on success)."""
    if _session_factory is None:
        init_db()
    assert _session_factory is not None

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_password_hasher() -> Argon2PasswordHasher:
    """Return the shared Argon2 hasher."""
    return _password_hasher


def get_token_service() -> JwtTokenService:
    """Return the shared JWT token service."""
    return _token_service


def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SqlAlchemyUserRepository:
    """Build a user repository for the current request session."""
    return SqlAlchemyUserRepository(session)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    users: Annotated[SqlAlchemyUserRepository, Depends(get_user_repository)],
    tokens: Annotated[JwtTokenService, Depends(get_token_service)],
) -> User:
    """Require a valid Bearer JWT and return the authenticated user."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        subject = tokens.decode_access_token(credentials.credentials)
        user_id = UUID(subject)
    except (DomainError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await users.get_by_id(user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# Alias for protected routes (JWT only).
require_auth = get_current_user


def get_process_booking_emails_use_case(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProcessBookingEmailsUseCase:
    """Build the booking-email pipeline for the current request."""
    settings = get_settings()
    return ProcessBookingEmailsUseCase(
        accounts=settings.load_booking_providers().booking_providers,
        email_messages=SqlAlchemyEmailMessageRepository(session),
        reservas=SqlAlchemyReservaRepository(session),
        whatsapp=NoOpWhatsAppNotifier(),
    )


DbSession = Annotated[AsyncSession, Depends(get_db_session)]
UserRepo = Annotated[SqlAlchemyUserRepository, Depends(get_user_repository)]
PasswordHasherDep = Annotated[Argon2PasswordHasher, Depends(get_password_hasher)]
TokenServiceDep = Annotated[JwtTokenService, Depends(get_token_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]
ProcessBookingEmailsDep = Annotated[
    ProcessBookingEmailsUseCase,
    Depends(get_process_booking_emails_use_case),
]

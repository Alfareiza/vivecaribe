"""Business ports — persistence and auth contracts (no infra details)."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from vivecaribe.domain.enums import BookingProvider
from vivecaribe.domain.reserva import Reserva
from vivecaribe.domain.user import User


class ReservaRepository(Protocol):
    """Persistence port for ``Reserva`` aggregates."""

    async def get_by_id(self, reserva_id: UUID) -> Reserva | None:
        """Return a reservation by primary key, or ``None`` if missing."""
        ...

    async def get_by_provider_message_id(
        self,
        provider: BookingProvider,
        message_id: str,
    ) -> Reserva | None:
        """Return the reservation for the idempotency key, if any."""
        ...

    async def save(self, reserva: Reserva) -> Reserva:
        """Insert or update a reservation and return the persisted entity."""
        ...


class UserRepository(Protocol):
    """Persistence port for ``User`` accounts."""

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Return a user by primary key, or ``None`` if missing."""
        ...

    async def get_by_email(self, email: str) -> User | None:
        """Return a user by unique email, or ``None`` if missing."""
        ...

    async def save(self, user: User) -> User:
        """Insert or update a user and return the persisted entity."""
        ...


class PasswordHasher(Protocol):
    """Hash and verify passwords (implementation lives in infrastructure)."""

    def hash(self, password: str) -> str:
        """Return a one-way hash for ``password``."""
        ...

    def verify(self, password: str, password_hash: str) -> bool:
        """Return ``True`` if ``password`` matches ``password_hash``."""
        ...


class TokenService(Protocol):
    """Issue and validate access tokens (JWT in infrastructure)."""

    def create_access_token(self, *, subject: str, email: str) -> str:
        """Create a signed access token for ``subject`` (user id) and email."""
        ...

    def decode_access_token(self, token: str) -> str:
        """Return the subject (user id) embedded in ``token``.

        Raises:
            DomainError: If the token is invalid or expired (infra maps
                library errors onto domain errors at the boundary).
        """
        ...

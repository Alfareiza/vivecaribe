"""SQLAlchemy repositories implementing domain persistence ports."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vivecaribe.domain.enums import BookingProvider
from vivecaribe.domain.reserva import Reserva
from vivecaribe.domain.user import User
from vivecaribe.infrastructure.db.models import EmailORM, ReservaORM, UserORM


def _apply_fields(row: object, data: dict[str, object]) -> None:
    """Copy ``data`` keys onto an ORM instance."""
    for key, value in data.items():
        setattr(row, key, value)


class SqlAlchemyUserRepository:
    """``UserRepository`` backed by PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this repository to an open async session."""
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Return a user by primary key, or ``None`` if missing."""
        row = await self._session.get(UserORM, user_id)
        return User.model_validate(row) if row else None

    async def get_by_email(self, email: str) -> User | None:
        """Return a user by unique email, or ``None`` if missing."""
        result = await self._session.execute(
            select(UserORM).where(UserORM.email == email),
        )
        row = result.scalar_one_or_none()
        return User.model_validate(row) if row else None

    async def save(self, user: User) -> User:
        """Insert or update a user and return the persisted entity."""
        row = await self._session.get(UserORM, user.id)
        payload = user.model_dump()
        if row is None:
            row = UserORM(**payload)
            self._session.add(row)
        else:
            _apply_fields(row, payload)
        await self._session.flush()
        return User.model_validate(row)


class SqlAlchemyReservaRepository:
    """``ReservaRepository`` backed by PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this repository to an open async session."""
        self._session = session

    async def get_by_id(self, reserva_id: UUID) -> Reserva | None:
        """Return a reservation by primary key, or ``None`` if missing."""
        row = await self._session.get(ReservaORM, reserva_id)
        return Reserva.model_validate(row) if row else None

    async def get_by_provider_message_id(
        self,
        provider: BookingProvider,
        message_id: str,
    ) -> Reserva | None:
        """Return the reservation for the idempotency key, if any."""
        result = await self._session.execute(
            select(ReservaORM).where(
                ReservaORM.provider == provider.value,
                ReservaORM.message_id == message_id,
            ),
        )
        row = result.scalar_one_or_none()
        return Reserva.model_validate(row) if row else None

    async def save(self, reserva: Reserva) -> Reserva:
        """Insert or update a reservation and return the persisted entity."""
        row = await self._session.get(ReservaORM, reserva.id)
        payload = reserva.model_dump()
        payload["provider"] = reserva.provider.value
        payload["estado"] = reserva.estado.value
        if row is None:
            row = ReservaORM(**payload)
            self._session.add(row)
        else:
            _apply_fields(row, payload)
        await self._session.flush()
        return Reserva.model_validate(row)

    async def get_or_create(self, reserva: Reserva) -> tuple[Reserva, bool]:
        """Return existing reserva by ``(provider, message_id)`` or insert.

        Returns:
            ``(entity, created)`` where ``created`` is ``True`` on insert.
        """
        existing = await self.get_by_provider_message_id(
            reserva.provider,
            reserva.message_id,
        )
        if existing is not None:
            return existing, False
        return await self.save(reserva), True


class EmailRepository:
    """Persist automation emails (ORM only — no domain port yet)."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this repository to an open async session."""
        self._session = session

    async def get_by_id(self, email_id: UUID) -> EmailORM | None:
        """Return an email row by primary key."""
        return await self._session.get(EmailORM, email_id)

    async def get_by_source_message_id(
        self,
        source: str,
        external_message_id: str,
    ) -> EmailORM | None:
        """Return an email by mailbox source + provider message id."""
        result = await self._session.execute(
            select(EmailORM).where(
                EmailORM.source == source,
                EmailORM.external_message_id == external_message_id,
            ),
        )
        return result.scalar_one_or_none()

    async def save(self, email: EmailORM) -> EmailORM:
        """Insert or update an email row."""
        merged = await self._session.merge(email)
        await self._session.flush()
        return merged

"""SQLAlchemy repositories for users, reservas, and email messages."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vivecaribe.domain.email_message import EmailMessage
from vivecaribe.domain.enums import BookingProvider
from vivecaribe.domain.reserva import Reserva
from vivecaribe.domain.user import User
from vivecaribe.infrastructure.db.models import EmailMessageORM, ReservaORM, UserORM


def _apply_fields(row: object, data: dict[str, object]) -> None:
    """Copy ``data`` keys onto an ORM instance."""
    for key, value in data.items():
        setattr(row, key, value)


class SqlAlchemyUserRepository:
    """User persistence backed by PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this repository to an open async session."""
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Return a user by primary key, or ``None`` if missing."""
        row = await self._session.get(UserORM, user_id)
        return User.model_validate(row) if row else None

    async def get_by_email(self, email: str) -> User | None:
        """Return a user by unique email address, or ``None`` if missing."""
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
        await self._session.refresh(row)
        return User.model_validate(row)


class SqlAlchemyReservaRepository:
    """Reserva persistence backed by PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this repository to an open async session."""
        self._session = session

    async def get_by_id(self, reserva_id: UUID) -> Reserva | None:
        """Return a reservation by primary key, or ``None`` if missing."""
        row = await self._session.get(ReservaORM, reserva_id)
        return Reserva.model_validate(row) if row else None

    async def get_by_booking_provider_reserva_reference(
        self,
        booking_provider: BookingProvider,
        reserva_reference: str,
    ) -> Reserva | None:
        """Return the reservation for the idempotency key, if any."""
        result = await self._session.execute(
            select(ReservaORM).where(
                ReservaORM.booking_provider == booking_provider.value,
                ReservaORM.reserva_reference == reserva_reference,
            ),
        )
        row = result.scalar_one_or_none()
        return Reserva.model_validate(row) if row else None

    async def save(self, reserva: Reserva) -> Reserva:
        """Insert or update a reservation and return the persisted entity."""
        row = await self._session.get(ReservaORM, reserva.id)
        payload = reserva.model_dump()
        payload["booking_provider"] = reserva.booking_provider.value
        payload["estado"] = reserva.estado.value
        if row is None:
            row = ReservaORM(**payload)
            self._session.add(row)
        else:
            _apply_fields(row, payload)
        await self._session.flush()
        await self._session.refresh(row)
        return Reserva.model_validate(row)

    async def get_or_create(self, reserva: Reserva) -> tuple[Reserva, bool]:
        """Return existing reserva by idempotency key or insert.

        Returns:
            ``(entity, created)`` where ``created`` is ``True`` on insert.
        """
        existing = await self.get_by_booking_provider_reserva_reference(
            reserva.booking_provider,
            reserva.reserva_reference,
        )
        if existing is not None:
            return existing, False
        return await self.save(reserva), True


class SqlAlchemyEmailMessageRepository:
    """Persist inbound mailbox messages (``EmailMessage`` ↔ ``EmailMessageORM``)."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this repository to an open async session."""
        self._session = session

    async def get_by_id(self, message_id: UUID) -> EmailMessage | None:
        """Return a message by primary key, or ``None``."""
        row = await self._session.get(EmailMessageORM, message_id)
        return _message_from_orm(row) if row else None

    async def get_by_source_mailbox_message_id(
        self,
        source: str,
        mailbox_message_id: str,
    ) -> EmailMessage | None:
        """Return a message by mailbox source + mailbox message id."""
        result = await self._session.execute(
            select(EmailMessageORM).where(
                EmailMessageORM.source == source,
                EmailMessageORM.mailbox_message_id == mailbox_message_id,
            ),
        )
        row = result.scalar_one_or_none()
        return _message_from_orm(row) if row else None

    async def save(self, message: EmailMessage) -> EmailMessage:
        """Insert or update a message and return the persisted model."""
        row = await self._session.get(EmailMessageORM, message.id)
        payload = _message_to_orm_payload(message)
        if row is None:
            row = EmailMessageORM(**payload)
            self._session.add(row)
        else:
            _apply_fields(row, payload)
        await self._session.flush()
        await self._session.refresh(row)
        return _message_from_orm(row)

    async def get_or_create(
        self,
        message: EmailMessage,
    ) -> tuple[EmailMessage, bool]:
        """Return existing message by ``(source, mailbox_message_id)`` or insert."""
        existing = await self.get_by_source_mailbox_message_id(
            message.source,
            message.mailbox_message_id,
        )
        if existing is not None:
            return existing, False
        return await self.save(message), True


def _message_to_orm_payload(message: EmailMessage) -> dict[str, object]:
    """Map ``EmailMessage`` fields onto ``EmailMessageORM`` column names."""
    return {
        "id": message.id,
        "source": message.source,
        "mailbox_message_id": message.mailbox_message_id,
        "sender": message.sender,
        "recipients": list(message.recipients),
        "subject": message.subject,
        "body_text": message.body_text,
        "body_html": message.body_html,
        "received_at": message.received_at,
        "metadata_": dict(message.metadata),
    }


def _message_from_orm(row: EmailMessageORM) -> EmailMessage:
    """Map an ``EmailMessageORM`` row to the domain ``EmailMessage`` model."""
    return EmailMessage(
        id=row.id,
        source=row.source,
        mailbox_message_id=row.mailbox_message_id,
        sender=row.sender,
        recipients=list(row.recipients or []),
        subject=row.subject,
        body_text=row.body_text,
        body_html=row.body_html,
        received_at=row.received_at,
        metadata=dict(row.metadata_ or {}),
    )

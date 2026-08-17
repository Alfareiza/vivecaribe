"""SQLAlchemy repositories for users, reservas, partidos, and email messages."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import ColumnElement, Date, and_, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from vivecaribe.domain.email_message import EmailMessage
from vivecaribe.domain.enums import BookingProvider, ReservaEstado
from vivecaribe.domain.partido import Partido
from vivecaribe.domain.refresh_token import RefreshToken
from vivecaribe.domain.reserva import Reserva
from vivecaribe.domain.user import User
from vivecaribe.infrastructure.db.models import (
    EmailMessageORM,
    PartidoORM,
    RefreshTokenORM,
    ReservaORM,
    UserORM,
)


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


class SqlAlchemyRefreshTokenRepository:
    """Refresh-token persistence backed by PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this repository to an open async session."""
        self._session = session

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        """Return a refresh token by its SHA-256 hash, or ``None``."""
        result = await self._session.execute(
            select(RefreshTokenORM).where(RefreshTokenORM.token_hash == token_hash),
        )
        row = result.scalar_one_or_none()
        return RefreshToken.model_validate(row) if row else None

    async def save(self, token: RefreshToken) -> RefreshToken:
        """Insert or update a refresh token and return the persisted entity."""
        row = await self._session.get(RefreshTokenORM, token.id)
        payload = token.model_dump()
        if row is None:
            row = RefreshTokenORM(**payload)
            self._session.add(row)
        else:
            _apply_fields(row, payload)
        await self._session.flush()
        await self._session.refresh(row)
        return RefreshToken.model_validate(row)

    async def revoke(
        self,
        token_id: UUID,
        *,
        replaced_by_id: UUID | None = None,
        revoked_at: datetime | None = None,
    ) -> None:
        """Mark a single refresh token as revoked."""
        row = await self._session.get(RefreshTokenORM, token_id)
        if row is None:
            return
        row.revoked_at = revoked_at or datetime.now(UTC)
        if replaced_by_id is not None:
            row.replaced_by_id = replaced_by_id
        await self._session.flush()

    async def revoke_family(
        self,
        family_id: UUID,
        *,
        revoked_at: datetime | None = None,
    ) -> int:
        """Revoke all non-revoked tokens in a rotation family. Return count."""
        when = revoked_at or datetime.now(UTC)
        result = await self._session.execute(
            select(RefreshTokenORM).where(
                RefreshTokenORM.family_id == family_id,
                RefreshTokenORM.revoked_at.is_(None),
            ),
        )
        rows = result.scalars().all()
        for row in rows:
            row.revoked_at = when
        await self._session.flush()
        return len(rows)


class SqlAlchemyReservaRepository:
    """Reserva persistence backed by PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this repository to an open async session."""
        self._session = session

    async def get_by_id(self, reserva_id: UUID) -> Reserva | None:
        """Return a non-deleted reservation by primary key, or ``None``."""
        result = await self._session.execute(
            select(ReservaORM).where(
                ReservaORM.id == reserva_id,
                ReservaORM.deleted_at.is_(None),
            ),
        )
        row = result.scalar_one_or_none()
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
                # ReservaORM.deleted_at.is_(None),  # Si la reserva ha sido eliminada igual la deberia retornar
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
        payload["tipo_tour"] = (
            reserva.tipo_tour.value if reserva.tipo_tour is not None else None
        )
        payload["meeting_point"] = (
            reserva.meeting_point.value
            if reserva.meeting_point is not None
            else None
        )
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

    async def list(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        estado: ReservaEstado | None = None,
        booking_provider: BookingProvider | None = None,
        fecha_evento_from: date | None = None,
        fecha_evento_to: date | None = None,
        ciudad: str | None = None,
        unassigned_only: bool = False,
    ) -> tuple[list[Reserva], int]:
        """Return a filtered page of non-deleted reservations.

        Filters compose with AND. Omitted filters are unconstrained.
        When either fecha bound is set, rows with null ``fecha_evento`` are
        excluded. Bounds are inclusive America/Bogota calendar days.
        ``ciudad`` matches ``ciudad_experiencia`` exactly (case-insensitive).
        ``unassigned_only`` restricts to rows with no linked partido.
        Ordered by ``fecha_evento`` descending (nulls last).
        """
        filters: list[ColumnElement[bool]] = [ReservaORM.deleted_at.is_(None)]
        if estado is not None:
            filters.append(ReservaORM.estado == estado.value)
        if booking_provider is not None:
            filters.append(
                ReservaORM.booking_provider == booking_provider.value,
            )
        if ciudad is not None:
            filters.append(func.lower(ReservaORM.ciudad_experiencia) == ciudad.lower())
        if unassigned_only:
            filters.append(ReservaORM.partido_id.is_(None))
        if fecha_evento_from is not None or fecha_evento_to is not None:
            filters.append(ReservaORM.fecha_evento.is_not(None))
            event_day = cast(
                func.timezone("America/Bogota", ReservaORM.fecha_evento),
                Date,
            )
            if fecha_evento_from is not None:
                filters.append(event_day >= fecha_evento_from)
            if fecha_evento_to is not None:
                filters.append(event_day <= fecha_evento_to)

        where_clause = and_(*filters)
        total_result = await self._session.execute(
            select(func.count()).select_from(ReservaORM).where(where_clause),
        )
        total = total_result.scalar_one()
        result = await self._session.execute(
            select(ReservaORM)
            .where(where_clause)
            .order_by(ReservaORM.fecha_evento.desc().nulls_last())
            .offset(skip)
            .limit(limit),
        )
        items = [Reserva.model_validate(row) for row in result.scalars()]
        return items, total

    async def soft_delete(self, reserva_id: UUID) -> bool:
        """Mark a reservation as deleted. Return ``False`` if missing."""
        result = await self._session.execute(
            select(ReservaORM).where(
                ReservaORM.id == reserva_id,
                ReservaORM.deleted_at.is_(None),
            ),
        )
        row = result.scalar_one_or_none()
        if row is None:
            return False
        now = datetime.now(UTC)
        row.deleted_at = now
        row.updated_at = now
        await self._session.flush()
        return True

    async def list_by_partido(self, partido_id: UUID) -> list[Reserva]:
        """Return all non-deleted reservations linked to ``partido_id``."""
        result = await self._session.execute(
            select(ReservaORM).where(
                ReservaORM.partido_id == partido_id,
                ReservaORM.deleted_at.is_(None),
            ),
        )
        return [Reserva.model_validate(row) for row in result.scalars()]

    async def unlink_partido(self, partido_id: UUID) -> int:
        """Clear ``partido_id`` on every reservation linked to it. Return count."""
        result = await self._session.execute(
            select(ReservaORM).where(ReservaORM.partido_id == partido_id),
        )
        rows = result.scalars().all()
        now = datetime.now(UTC)
        for row in rows:
            row.partido_id = None
            row.updated_at = now
        await self._session.flush()
        return len(rows)


class SqlAlchemyPartidoRepository:
    """Partido persistence backed by PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this repository to an open async session."""
        self._session = session

    async def get_by_id(self, partido_id: UUID) -> Partido | None:
        """Return a non-deleted partido by primary key, or ``None``."""
        result = await self._session.execute(
            select(PartidoORM).where(
                PartidoORM.id == partido_id,
                PartidoORM.deleted_at.is_(None),
            ),
        )
        row = result.scalar_one_or_none()
        return Partido.model_validate(row) if row else None

    async def save(self, partido: Partido) -> Partido:
        """Insert or update a partido and return the persisted entity."""
        row = await self._session.get(PartidoORM, partido.id)
        payload = partido.model_dump()
        payload["nombre_campeonato"] = partido.nombre_campeonato.value
        payload["estadio"] = partido.estadio.value
        payload["ciudad"] = partido.ciudad.value
        if row is None:
            row = PartidoORM(**payload)
            self._session.add(row)
        else:
            _apply_fields(row, payload)
        await self._session.flush()
        await self._session.refresh(row)
        return Partido.model_validate(row)

    async def list(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        ciudad: str | None = None,
        fecha_from: datetime | None = None,
        fecha_to: datetime | None = None,
        q: str | None = None,
    ) -> tuple[list[dict[str, object]], int]:
        """Return a filtered page of non-deleted partidos, each with a reservas_count.

        Filters compose with AND. ``q`` does a case-insensitive search across
        ``equipo_local``, ``equipo_visitante``, and ``ciudad``. Ordered by
        ``fecha`` ascending (soonest first).

        Each item is a plain dict (partido fields + ``reservas_count``), built
        from a single LEFT JOIN + COUNT query — no N+1. The non-deleted filter
        on reservas lives in the join's ON clause, not WHERE, so a partido
        whose reservas are all soft-deleted still appears (with count 0)
        instead of being dropped from the page entirely.
        """
        filters: list[ColumnElement[bool]] = [PartidoORM.deleted_at.is_(None)]
        if ciudad is not None:
            filters.append(PartidoORM.ciudad.ilike(f"%{ciudad}%"))
        if fecha_from is not None:
            filters.append(PartidoORM.fecha >= fecha_from)
        if fecha_to is not None:
            filters.append(PartidoORM.fecha <= fecha_to)
        if q is not None:
            pattern = f"%{q}%"
            filters.append(
                PartidoORM.equipo_local.ilike(pattern)
                | PartidoORM.equipo_visitante.ilike(pattern)
                | PartidoORM.ciudad.ilike(pattern),
            )

        where_clause = and_(*filters)

        total_result = await self._session.execute(
            select(func.count()).select_from(PartidoORM).where(where_clause),
        )
        total = total_result.scalar_one()

        result = await self._session.execute(
            select(PartidoORM, func.count(ReservaORM.id).label("reservas_count"))
            .outerjoin(
                ReservaORM,
                and_(
                    ReservaORM.partido_id == PartidoORM.id,
                    ReservaORM.deleted_at.is_(None),
                ),
            )
            .where(where_clause)
            .group_by(PartidoORM.id)
            .order_by(PartidoORM.fecha.asc())
            .offset(skip)
            .limit(limit),
        )

        items = [
            {**Partido.model_validate(row).model_dump(), "reservas_count": count}
            for row, count in result.all()
        ]
        return items, total

    async def soft_delete(self, partido_id: UUID) -> bool:
        """Mark a partido as deleted. Return ``False`` if missing."""
        result = await self._session.execute(
            select(PartidoORM).where(
                PartidoORM.id == partido_id,
                PartidoORM.deleted_at.is_(None),
            ),
        )
        row = result.scalar_one_or_none()
        if row is None:
            return False
        now = datetime.now(UTC)
        row.deleted_at = now
        row.updated_at = now
        await self._session.flush()
        return True


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

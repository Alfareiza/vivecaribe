"""SQLAlchemy ORM models for users, email_messages, reservas, and partidos."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all ORM tables."""


class UserORM(Base):
    """Persisted platform user."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class RefreshTokenORM(Base):
    """Persisted opaque refresh token (hash only; raw value never stored)."""

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
        Index("ix_refresh_tokens_user_id", "user_id"),
        Index("ix_refresh_tokens_family_id", "family_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    family_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    replaced_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("refresh_tokens.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class EmailMessageORM(Base):
    """Persisted inbound mailbox message (automation source)."""

    __tablename__ = "email_messages"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "mailbox_message_id",
            name="uq_email_messages_source_mailbox_message_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    mailbox_message_id: Mapped[str] = mapped_column(String(512), nullable=False)
    sender: Mapped[str] = mapped_column(String(320), nullable=False)
    recipients: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    subject: Mapped[str] = mapped_column(String(998), nullable=False, default="")
    body_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    body_html: Mapped[str] = mapped_column(Text, nullable=False, default="")
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ReservaORM(Base):
    """Persisted booking / reservation."""

    __tablename__ = "reservas"
    __table_args__ = (
        UniqueConstraint(
            "booking_provider",
            "reserva_reference",
            name="uq_reservas_booking_provider_reserva_reference",
        ),
        Index("ix_reservas_notificado_whatsapp", "notificado_whatsapp"),
        Index("ix_reservas_estado", "estado"),
        Index("ix_reservas_booking_provider", "booking_provider"),
        Index("ix_reservas_fecha_evento", "fecha_evento"),
        Index("ix_reservas_fecha_email_recibido", "fecha_email_recibido"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    email_message_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("email_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    partido_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("partidos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    booking_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    reserva_reference: Mapped[str] = mapped_column(String(512), nullable=False)
    sender: Mapped[str | None] = mapped_column(String(320), nullable=True)
    estado: Mapped[str] = mapped_column(String(32), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(998), nullable=True)
    fecha_email_recibido: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    nombre_experiencia: Mapped[str] = mapped_column(String(512), nullable=False)
    ciudad_experiencia: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha_evento: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    participants: Mapped[int] = mapped_column(nullable=False, default=0)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    pais_del_visitante: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    moneda: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    income: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    notificado_whatsapp: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    notas_cliente: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tipo_tour: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notas_personales: Mapped[str | None] = mapped_column(String(255), nullable=True)
    costos: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    meeting_point: Mapped[str | None] = mapped_column(String(32), nullable=True)
    lugar_de_recogida: Mapped[str | None] = mapped_column(String(64), nullable=True)
    income_estimado: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    trm_estimado: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    trm_final: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    income_final: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    profit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    percentage_profit: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    menores_de_edad: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class GastoORM(Base):
    """Persisted partido-level expense in one fixed category.

    At most one row exists per ``(partido_id, categoria)`` — the operator
    sets one amount per category rather than a repeatable list.
    """

    __tablename__ = "gastos"
    __table_args__ = (
        UniqueConstraint(
            "partido_id",
            "categoria",
            name="uq_gastos_partido_id_categoria",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    partido_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("partidos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    categoria: Mapped[str] = mapped_column(String(32), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class GastoReservaSplitORM(Base):
    """Persisted per-reserva share of a ``GastoORM``.

    Recomputed (deleted and reinserted) by
    ``SqlAlchemyGastoRepository`` / ``_recompute_gasto_splits`` whenever a
    gasto changes or a partido's linked reservas change. Feeds the owning
    reserva's derived ``costos``.
    """

    __tablename__ = "gasto_reserva_splits"
    __table_args__ = (
        UniqueConstraint(
            "gasto_id",
            "reserva_id",
            name="uq_gasto_reserva_splits_gasto_id_reserva_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    gasto_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("gastos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reserva_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("reservas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)


class PartidoORM(Base):
    """Persisted football match, optionally linked to many reservas."""

    __tablename__ = "partidos"
    __table_args__ = (
        Index("ix_partidos_fecha", "fecha"),
        Index("ix_partidos_ciudad", "ciudad"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    equipo_local: Mapped[str] = mapped_column(String(25), nullable=False)
    equipo_visitante: Mapped[str] = mapped_column(String(25), nullable=False)
    nombre_campeonato: Mapped[str] = mapped_column(String(50), nullable=False)
    estadio: Mapped[str] = mapped_column(String(25), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ciudad: Mapped[str] = mapped_column(String(50), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

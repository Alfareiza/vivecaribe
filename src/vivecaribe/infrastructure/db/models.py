"""SQLAlchemy ORM models for users, emails, and reservas."""

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


class EmailORM(Base):
    """Persisted inbound email (automation source). No domain entity yet."""

    __tablename__ = "emails"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "external_message_id",
            name="uq_emails_source_external_message_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    external_message_id: Mapped[str] = mapped_column(String(512), nullable=False)
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
            "provider",
            "message_id",
            name="uq_reservas_provider_message_id",
        ),
        Index("ix_reservas_notificado_whatsapp", "notificado_whatsapp"),
        Index("ix_reservas_estado", "estado"),
        Index("ix_reservas_fecha_email_recibido", "fecha_email_recibido"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    email_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("emails.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    message_id: Mapped[str] = mapped_column(String(512), nullable=False)
    sender: Mapped[str] = mapped_column(String(320), nullable=False)
    estado: Mapped[str] = mapped_column(String(32), nullable=False)
    subject: Mapped[str] = mapped_column(String(998), nullable=False, default="")
    fecha_email_recibido: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
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

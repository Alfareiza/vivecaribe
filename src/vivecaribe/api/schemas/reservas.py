"""Request/response schemas for reserva CRUD endpoints."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from vivecaribe.domain.enums import BookingProvider, ReservaEstado


class ReservaCreate(BaseModel):
    """Payload for ``POST /reservas``."""

    source: str
    booking_provider: BookingProvider
    reserva_reference: str
    sender: str
    estado: ReservaEstado
    subject: str
    fecha_email_recibido: datetime
    nombre_experiencia: str
    ciudad_experiencia: str
    fecha_evento: datetime | None = None
    participants: int = Field(ge=0)
    customer_name: str
    phone: str = ""
    pais_del_visitante: str = ""
    moneda: str = "USD"
    price: Decimal
    income: Decimal
    notificado_whatsapp: bool = False
    email_message_id: UUID | None = None
    user_id: UUID | None = None


class ReservaUpdate(BaseModel):
    """Partial payload for ``PATCH /reservas/{id}``.

    Identity and audit fields are intentionally omitted so they stay
    immutable through this endpoint.
    """

    estado: ReservaEstado | None = None
    nombre_experiencia: str | None = None
    ciudad_experiencia: str | None = None
    fecha_evento: datetime | None = None
    participants: int | None = Field(default=None, ge=0)
    customer_name: str | None = None
    phone: str | None = None
    pais_del_visitante: str | None = None
    moneda: str | None = None
    price: Decimal | None = None
    income: Decimal | None = None
    notificado_whatsapp: bool | None = None
    subject: str | None = None


class ReservaResponse(BaseModel):
    """Public reservation representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: str
    booking_provider: BookingProvider
    reserva_reference: str
    sender: str
    estado: ReservaEstado
    subject: str
    fecha_email_recibido: datetime
    nombre_experiencia: str
    ciudad_experiencia: str
    fecha_evento: datetime | None
    participants: int
    customer_name: str
    phone: str
    pais_del_visitante: str
    moneda: str
    price: Decimal
    income: Decimal
    notificado_whatsapp: bool
    email_message_id: UUID | None
    user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class ReservaListResponse(BaseModel):
    """Paginated reservation list."""

    total: int
    items: list[ReservaResponse]

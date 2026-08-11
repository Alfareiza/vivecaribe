"""Request/response schemas for reserva CRUD endpoints."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, computed_field

from vivecaribe.domain.enums import BookingProvider, ReservaEstado
from vivecaribe.domain.reserva import Reserva

_BOGOTA = ZoneInfo("America/Bogota")


def _es_hoy(
    fecha_evento: datetime | None,
    *,
    now: datetime | None = None,
) -> bool:
    """True when ``fecha_evento`` is today's calendar day in America/Bogota."""
    if fecha_evento is None:
        return False
    current = now if now is not None else datetime.now(_BOGOTA)
    if current.tzinfo is None:
        current = current.replace(tzinfo=_BOGOTA)
    else:
        current = current.astimezone(_BOGOTA)
    event = (
        fecha_evento.replace(tzinfo=_BOGOTA)
        if fecha_evento.tzinfo is None
        else fecha_evento.astimezone(_BOGOTA)
    )
    return event.date() == current.date()


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


class ReservaShortItem(BaseModel):
    """Slim reservation row for ``GET /reservas`` list pages."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    booking_provider: BookingProvider
    ciudad_experiencia: str
    nombre_experiencia: str
    participants: int
    pais_del_visitante: str
    phone: str
    fecha_evento: datetime | None
    customer_name: str
    moneda: str
    price: Decimal
    income: Decimal

    @computed_field  # type: ignore[prop-decorator]
    @property
    def es_hoy(self) -> bool:
        """Whether ``fecha_evento`` is today in America/Bogota."""
        return _es_hoy(self.fecha_evento)


class ReservaResponse(Reserva):
    """Public reservation representation (detail / mutations)."""

    deleted_at: datetime | None = Field(default=None, exclude=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def es_hoy(self) -> bool:
        """Whether ``fecha_evento`` is today in America/Bogota."""
        return _es_hoy(self.fecha_evento)


class ReservaListResponse(BaseModel):
    """Paginated reservation list."""

    total: int
    items: list[ReservaShortItem]

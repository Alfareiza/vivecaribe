"""Request/response schemas for reserva CRUD endpoints."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from vivecaribe.api.schemas.gastos import GastoShareItem
from vivecaribe.domain.enums import (
    BookingProvider,
    MeetingPoint,
    ReservaEstado,
    TipoTour,
)
from vivecaribe.domain.reserva import Reserva


def _es_hoy(fecha_evento: datetime | None) -> bool:
    """True when ``fecha_evento`` falls on today's calendar date."""
    if fecha_evento is None:
        return False
    return fecha_evento.date() == datetime.now().date()


class ReservaCreate(BaseModel):
    """Payload for ``POST /reservas``."""

    source: str = Field(max_length=64)
    booking_provider: BookingProvider
    reserva_reference: str = Field(max_length=512)
    sender: str | None = Field(default=None, max_length=320)
    estado: ReservaEstado
    subject: str | None = Field(default=None, max_length=998)
    fecha_email_recibido: datetime | None = None
    nombre_experiencia: str = Field(max_length=512)
    ciudad_experiencia: str = Field(max_length=255)
    fecha_evento: datetime | None = None
    participants: int = Field(ge=0)
    customer_name: str = Field(max_length=255)
    phone: str = Field(default="", max_length=64)
    pais_del_visitante: str = Field(default="", max_length=128)
    moneda: str = Field(default="USD", max_length=8)
    price: Decimal = Field(gt=0)
    income: Decimal = Field(gt=0)
    notificado_whatsapp: bool = False
    notas_cliente: str | None = Field(default=None, max_length=5000)
    tipo_tour: TipoTour | None = None
    notas_personales: str | None = Field(default=None, max_length=5000)
    meeting_point: MeetingPoint | None = None
    lugar_de_recogida: str | None = Field(default=None, max_length=64)
    income_estimado: Decimal | None = None
    trm_estimado: Decimal | None = None
    menores_de_edad: bool = False
    email_message_id: UUID | None = None
    user_id: UUID | None = None
    partido_id: UUID | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone_prefix(cls, value: str) -> str:
        """Require a leading ``+`` (E.164-style) when a phone is provided."""
        if value and not value.startswith("+"):
            raise ValueError("phone must start with '+' (E.164 format)")
        return value


class ReservaUpdate(BaseModel):
    """Partial payload for ``PATCH /reservas/{id}``.

    Identity and audit fields are intentionally omitted so they stay
    immutable through this endpoint. ``paid_at`` is derived server-side
    from ``booking_provider`` + ``fecha_evento`` and is not writable here.
    ``trm_estimado`` is normally set at creation from the auto-fetched rate;
    this endpoint accepts it only to fill in a still-null value (e.g. a
    legacy reserva) — once set, the router silently drops further attempts
    to change it. ``costos`` is not writable here: it's derived server-side
    from this reserva's share of its partido's gastos (see
    ``vivecaribe.api.routers.gastos``). ``profit``/``percentage_profit`` are
    in turn derived from income, costos, and ``trm_final``.
    """

    estado: ReservaEstado | None = None
    booking_provider: BookingProvider | None = None
    nombre_experiencia: str | None = Field(default=None, max_length=512)
    ciudad_experiencia: str | None = Field(default=None, max_length=255)
    fecha_evento: datetime | None = None
    participants: int | None = Field(default=None, ge=0)
    customer_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=64)
    pais_del_visitante: str | None = Field(default=None, max_length=128)
    moneda: str | None = Field(default=None, max_length=8)
    price: Decimal | None = Field(default=None, gt=0)
    income: Decimal | None = Field(default=None, gt=0)
    notificado_whatsapp: bool | None = None
    subject: str | None = Field(default=None, max_length=998)
    notas_cliente: str | None = Field(default=None, max_length=5000)
    tipo_tour: TipoTour | None = None
    notas_personales: str | None = Field(default=None, max_length=5000)
    meeting_point: MeetingPoint | None = None
    lugar_de_recogida: str | None = Field(default=None, max_length=64)
    income_estimado: Decimal | None = None
    trm_estimado: Decimal | None = None
    trm_final: Decimal | None = None
    menores_de_edad: bool | None = None
    partido_id: UUID | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone_prefix(cls, value: str | None) -> str | None:
        """Require a leading ``+`` (E.164-style) when a phone is provided."""
        if value and not value.startswith("+"):
            raise ValueError("phone must start with '+' (E.164 format)")
        return value


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
    partido_id: UUID | None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def es_hoy(self) -> bool:
        """Whether ``fecha_evento`` is today's calendar date."""
        return _es_hoy(self.fecha_evento)


class ReservaResponse(Reserva):
    """Public reservation representation (detail / mutations).

    ``gastos`` lists this reserva's computed share of each of its partido's
    registered gasto categories (read-only here; gastos are set from the
    Partido side via ``PUT``/``DELETE /partidos/{id}/gastos/{categoria}``).
    """

    deleted_at: datetime | None = Field(default=None, exclude=True)
    gastos: list[GastoShareItem] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def es_hoy(self) -> bool:
        """Whether ``fecha_evento`` is today's calendar date."""
        return _es_hoy(self.fecha_evento)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def gastos_total(self) -> Decimal:
        """Sum of this reserva's share across all gasto categories."""
        return sum((g.monto for g in self.gastos), Decimal(0))


class ReservaListResponse(BaseModel):
    """Paginated reservation list."""

    total: int
    items: list[ReservaShortItem]

"""``Reserva`` — core booking entity."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, Self
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, model_validator

from vivecaribe.domain.enums import (
    BookingProvider,
    MeetingPoint,
    ReservaEstado,
    TipoTour,
)

_BOGOTA = ZoneInfo("America/Bogota")


def compute_paid_at(
    booking_provider: BookingProvider,
    fecha_evento: datetime | None,
) -> datetime | None:
    """Derive expected payout date from provider + event day (Bogota).

    Returns ``None`` when ``fecha_evento`` is missing.
    """
    if fecha_evento is None:
        return None

    event = (
        fecha_evento.replace(tzinfo=_BOGOTA)
        if fecha_evento.tzinfo is None
        else fecha_evento.astimezone(_BOGOTA)
    )
    event_day = event.date()

    if booking_provider in (
        BookingProvider.GETYOURGUIDE,
        BookingProvider.VIATOR,
    ):
        paid_day = _marketplace_payout_day(event_day)
    elif booking_provider is BookingProvider.PROPIO:
        paid_day = event_day + timedelta(days=1)
    elif booking_provider is BookingProvider.HOMEFANS:
        paid_day = _next_thursday_after(event_day)
    else:  # pragma: no cover — StrEnum exhaustiveness
        return None

    return datetime(
        paid_day.year,
        paid_day.month,
        paid_day.day,
        tzinfo=_BOGOTA,
    )


def _marketplace_payout_day(event_day: date) -> date:
    """GYG / Viator: 7th of next month, or 9th when the 7th is weekend."""
    if event_day.month == 12:
        candidate = date(event_day.year + 1, 1, 7)
    else:
        candidate = date(event_day.year, event_day.month + 1, 7)
    # Saturday=5, Sunday=6
    if candidate.weekday() >= 5:
        return candidate.replace(day=9)
    return candidate


def _next_thursday_after(event_day: date) -> date:
    """Homefans: next Thursday; Wed/Thu events use the following week's Thursday."""
    # Monday=0 … Thursday=3
    days_ahead = (3 - event_day.weekday()) % 7
    if days_ahead <= 1:
        days_ahead += 7
    return event_day + timedelta(days=days_ahead)


class Reserva(BaseModel):
    """Business booking created from an ingested booking email.

    Identity for idempotency is the pair
    ``(booking_provider, reserva_reference)``.
    ``email_message_id`` optionally links back to an ingested mailbox message;
    HTML body content itself does not live on this entity.

    ``paid_at`` is always derived from ``booking_provider`` + ``fecha_evento``
    (America/Bogota calendar rules) on construction, assignment, and
    ``model_copy``.
    """

    model_config = ConfigDict(from_attributes=True, validate_assignment=True)

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
    participants: int = Field(ge=0)
    customer_name: str
    phone: str
    pais_del_visitante: str
    moneda: str
    price: Decimal
    income: Decimal
    notificado_whatsapp: bool = False
    notas_cliente: str | None = Field(default=None, max_length=255)
    tipo_tour: TipoTour | None = None
    notas_personales: str | None = Field(default=None, max_length=255)
    costos: Decimal | None = None
    meeting_point: MeetingPoint | None = None
    lugar_de_recogida: str | None = Field(default=None, max_length=64)
    income_estimado: Decimal | None = None
    profit: Decimal | None = None
    percentage: Decimal | None = None
    menores_de_edad: bool = False
    paid_at: datetime | None = None
    email_message_id: UUID | None = None
    user_id: UUID | None = None
    deleted_at: datetime | None = None
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def _sync_paid_at(self) -> Self:
        """Keep ``paid_at`` aligned with provider + event date."""
        expected = compute_paid_at(self.booking_provider, self.fecha_evento)
        if self.paid_at != expected:
            # Bypass validate_assignment to avoid re-entrant validation.
            object.__setattr__(self, "paid_at", expected)
        return self

    def model_copy(
        self,
        *,
        update: Mapping[str, Any] | None = None,
        deep: bool = False,
    ) -> Self:
        """Copy then re-validate so derived ``paid_at`` stays in sync."""
        copied = super().model_copy(update=update, deep=deep)
        return type(self).model_validate(copied.model_dump())

    def to_dict(self) -> dict[str, Any]:
        """Serialize this reservation to a JSON-friendly dict."""
        return self.model_dump(mode="json")

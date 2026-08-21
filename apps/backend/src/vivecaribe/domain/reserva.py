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
    elif booking_provider is BookingProvider.VAYARA:
        paid_day = event_day
    else:  # OTRO and any future provider: no payout formula defined yet
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


def compute_income_final(
    moneda: str,
    income: Decimal,
    trm_final: Decimal | None,
) -> Decimal | None:
    """Derive the actual COP income received: ``income`` converted at the
    real day-of-payment rate.

    A COP reserva needs no conversion. A non-COP reserva needs
    ``trm_final`` (only known once payment is received) — returns
    ``None`` until then.
    """
    if moneda == "COP":
        return income
    if trm_final is None:
        return None
    return (income * trm_final).quantize(Decimal("0.01"))


def compute_profit(
    income_final: Decimal | None,
    costos: Decimal | None,
) -> tuple[Decimal | None, Decimal | None]:
    """Derive ``(profit, percentage_profit)`` from actual COP income and costos.

    ``costos`` is always COP. Returns ``(None, None)`` while either input is
    still missing (e.g. ``income_final`` isn't known until ``trm_final``
    is filled in for a non-COP reserva).
    """
    if income_final is None or costos is None:
        return None, None

    profit = (income_final - costos).quantize(Decimal("0.01"))
    percentage_profit = (
        (profit / costos * 100).quantize(Decimal("0.01")) if costos != 0 else None
    )
    return profit, percentage_profit


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
    sender: str | None
    estado: ReservaEstado
    motivo_cancelacion: str | None = Field(default=None, max_length=255)
    subject: str | None
    fecha_email_recibido: datetime | None
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
    notas_cliente: str | None = Field(default=None, max_length=5000)
    tipo_tour: TipoTour | None = None
    notas_personales: str | None = Field(default=None, max_length=5000)
    costos: Decimal | None = None
    meeting_point: MeetingPoint | None = None
    lugar_de_recogida: str | None = Field(default=None, max_length=64)
    income_estimado: Decimal | None = None
    trm_estimado: Decimal | None = None
    trm_final: Decimal | None = None
    income_final: Decimal | None = None
    profit: Decimal | None = None
    percentage_profit: Decimal | None = None
    menores_de_edad: bool = False
    paid_at: datetime | None = None
    email_message_id: UUID | None = None
    user_id: UUID | None = None
    partido_id: UUID | None = None
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

    @model_validator(mode="after")
    def _sync_income_final(self) -> Self:
        """Keep ``income_final`` aligned with income, moneda, and trm_final."""
        income_final = compute_income_final(self.moneda, self.income, self.trm_final)
        if self.income_final != income_final:
            # Bypass validate_assignment to avoid re-entrant validation.
            object.__setattr__(self, "income_final", income_final)
        return self

    @model_validator(mode="after")
    def _sync_profit(self) -> Self:
        """Keep ``profit``/``percentage_profit`` aligned with their inputs."""
        profit, percentage_profit = compute_profit(self.income_final, self.costos)
        if self.profit != profit:
            # Bypass validate_assignment to avoid re-entrant validation.
            object.__setattr__(self, "profit", profit)
        if self.percentage_profit != percentage_profit:
            object.__setattr__(self, "percentage_profit", percentage_profit)
        return self

    @model_validator(mode="after")
    def check_tipo_tour(self) -> Self:
        """Set ``tipo_tour`` when the experience name matches football keywords."""
        football_tours_keywords = ("match", "soccer", "football")
        name = self.nombre_experiencia.lower()
        if any(keyword in name for keyword in football_tours_keywords):
            # Bypass validate_assignment to avoid re-entrant validation.
            object.__setattr__(self, "tipo_tour", TipoTour.FOOTBALL_TOUR)
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

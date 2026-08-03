"""``Reserva`` — core booking entity."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from vivecaribe.domain.enums import BookingProvider, ReservaEstado


class Reserva(BaseModel):
    """Business booking created from an ingested booking email.

    Identity for idempotency is the pair
    ``(booking_provider, reserva_reference)``.
    ``email_message_id`` optionally links back to an ingested mailbox message;
    HTML body content itself does not live on this entity.
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
    email_message_id: UUID | None = None
    user_id: UUID | None = None
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Serialize this reservation to a JSON-friendly dict."""
        return self.model_dump(mode="json")

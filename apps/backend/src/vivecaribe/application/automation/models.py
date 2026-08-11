"""Automation drafts assembled from booking extractors."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from vivecaribe.domain.enums import BookingProvider, ReservaEstado
from vivecaribe.domain.reserva import Reserva, compute_paid_at


class ReservaDraft(BaseModel):
    """Extractor output before persistence enrichment."""

    model_config = ConfigDict(validate_assignment=True)

    booking_provider: BookingProvider
    reserva_reference: str
    estado: ReservaEstado = ReservaEstado.CONFIRMADA
    nombre_experiencia: str
    ciudad_experiencia: str
    fecha_evento: datetime | None = None
    participants: int = Field(ge=0, default=0)
    customer_name: str
    phone: str = ""
    pais_del_visitante: str = ""
    moneda: str = "USD"
    price: Decimal
    income: Decimal

    def to_reserva(
        self,
        *,
        source: str,
        sender: str,
        subject: str,
        fecha_email_recibido: datetime,
        email_message_id: UUID | None = None,
        notificado_whatsapp: bool = False,
    ) -> Reserva:
        """Build a domain ``Reserva`` from this draft plus message context."""
        now = datetime.now(UTC)
        return Reserva(
            source=source,
            booking_provider=self.booking_provider,
            reserva_reference=self.reserva_reference,
            sender=sender,
            estado=self.estado,
            subject=subject,
            fecha_email_recibido=fecha_email_recibido,
            nombre_experiencia=self.nombre_experiencia,
            ciudad_experiencia=self.ciudad_experiencia,
            fecha_evento=self.fecha_evento,
            participants=self.participants,
            customer_name=self.customer_name,
            phone=self.phone,
            pais_del_visitante=self.pais_del_visitante,
            moneda=self.moneda,
            price=self.price,
            income=self.income,
            notificado_whatsapp=notificado_whatsapp,
            email_message_id=email_message_id,
            paid_at=compute_paid_at(self.booking_provider, self.fecha_evento),
            created_at=now,
            updated_at=now,
        )

"""NoOp WhatsApp notifier."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from vivecaribe.domain.enums import BookingProvider, ReservaEstado
from vivecaribe.domain.reserva import Reserva
from vivecaribe.infrastructure.integrations.whatsapp import NoOpWhatsAppNotifier


@pytest.mark.asyncio
async def test_noop_whatsapp_notify_returns_false() -> None:
    """NoOp notifier never reports a successful send."""
    reserva = Reserva(
        source="gmail",
        booking_provider=BookingProvider.GETYOURGUIDE,
        reserva_reference="R1",
        sender="a@b.com",
        estado=ReservaEstado.EN_PROGRESO,
        subject="s",
        fecha_email_recibido=datetime.now(UTC),
        nombre_experiencia="Tour",
        ciudad_experiencia="Cartagena",
        fecha_evento=None,
        participants=1,
        customer_name="Ada",
        phone="",
        pais_del_visitante="",
        moneda="USD",
        price=Decimal("10"),
        income=Decimal("10"),
    )
    assert await NoOpWhatsAppNotifier().notify(reserva) is False

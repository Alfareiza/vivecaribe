"""WhatsApp notifier — NoOp until Meta Business is approved."""

from __future__ import annotations

from vivecaribe.domain.reserva import Reserva
from vivecaribe.logging import logger


class NoOpWhatsAppNotifier:
    """Does not send messages; pipeline must not mark emails as read."""

    async def notify(self, reserva: Reserva) -> bool:
        """Log and return ``False`` (not a successful real send)."""
        logger.info(
            f"WhatsApp NoOp — not notifying reserva {reserva.id} "
            f"(booking_provider={reserva.booking_provider} "
            f"reserva_reference={reserva.reserva_reference})",
        )
        return False

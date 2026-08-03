"""WhatsApp notifier — NoOp until Meta Business is approved."""

from __future__ import annotations

from vivecaribe.domain.reserva import Reserva
from vivecaribe.logging import logger


class NoOpWhatsAppNotifier:
    """Does not send messages; pipeline must not mark emails as read."""

    async def notify(self, reserva: Reserva) -> bool:
        """Log and return ``False`` (not a successful real send)."""
        logger.info(
            "WhatsApp NoOp — not notifying reserva %s "
            "(booking_provider=%s reserva_reference=%s)",
            reserva.id,
            reserva.booking_provider,
            reserva.reserva_reference,
        )
        return False

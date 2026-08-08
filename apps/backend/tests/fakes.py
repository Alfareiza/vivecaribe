"""Shared in-memory fakes for automation pipeline tests."""

from __future__ import annotations

from vivecaribe.domain.email_message import EmailMessage
from vivecaribe.domain.reserva import Reserva
from vivecaribe.infrastructure.integrations.whatsapp import NoOpWhatsAppNotifier


class FakeMailbox:
    """In-memory mailbox client for use-case tests."""

    def __init__(self, messages: list[EmailMessage] | None = None) -> None:
        """Store messages that ``fetch_messages`` will return."""
        self.messages = list(messages or [])
        self.marked_read: list[str] = []

    async def fetch_messages(
        self,
        *,
        query: str,
        max_results: int = 30,
    ) -> list[EmailMessage]:
        """Return the preloaded messages (query ignored in tests)."""
        return self.messages[:max_results]

    async def mark_as_read(self, *, mailbox_message_id: str) -> None:
        """Record that a message was marked read."""
        self.marked_read.append(mailbox_message_id)


class FailingMailbox(FakeMailbox):
    """Mailbox whose ``fetch_messages`` always raises ``DomainError``."""

    def __init__(self, error: Exception) -> None:
        """Remember the error to raise on fetch."""
        super().__init__([])
        self.error = error

    async def fetch_messages(
        self,
        *,
        query: str,
        max_results: int = 30,
    ) -> list[EmailMessage]:
        """Raise the configured domain/transport failure."""
        raise self.error


class FakeEmailMessageStore:
    """In-memory email-message persistence."""

    def __init__(self) -> None:
        """Create an empty store keyed by ``(source, mailbox_message_id)``."""
        self.by_key: dict[tuple[str, str], EmailMessage] = {}

    async def get_or_create(
        self,
        message: EmailMessage,
    ) -> tuple[EmailMessage, bool]:
        """Return existing message or insert the new one."""
        key = (message.source, message.mailbox_message_id)
        existing = self.by_key.get(key)
        if existing is not None:
            return existing, False
        self.by_key[key] = message
        return message, True


class FakeReservaStore:
    """In-memory reserva persistence with get_or_create."""

    def __init__(self) -> None:
        """Create an empty store keyed by ``(booking_provider, reserva_reference)``."""
        self.by_key: dict[tuple[str, str], Reserva] = {}

    async def get_or_create(self, reserva: Reserva) -> tuple[Reserva, bool]:
        """Return existing reserva or insert the new one."""
        key = (reserva.booking_provider.value, reserva.reserva_reference)
        existing = self.by_key.get(key)
        if existing is not None:
            return existing, False
        self.by_key[key] = reserva
        return reserva, True

    async def save(self, reserva: Reserva) -> Reserva:
        """Upsert a reserva by booking provider / reserva_reference."""
        key = (reserva.booking_provider.value, reserva.reserva_reference)
        self.by_key[key] = reserva
        return reserva


class AlwaysNotifyWhatsApp(NoOpWhatsAppNotifier):
    """Test double that pretends Meta send succeeded."""

    async def notify(self, reserva: Reserva) -> bool:
        """Always report a successful WhatsApp send."""
        return True

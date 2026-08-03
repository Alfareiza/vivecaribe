"""Automation use cases — fetch, extract, persist, notify (no HTTP yet)."""

from __future__ import annotations

from vivecaribe.application.automation.models import ReservaDraft
from vivecaribe.application.automation.providers import EXTRACTORS, BaseExtractor
from vivecaribe.domain.email_message import EmailMessage
from vivecaribe.domain.enums import BookingProvider
from vivecaribe.domain.errors import DomainError, ValidationError
from vivecaribe.domain.reserva import Reserva
from vivecaribe.infrastructure.db.repositories import (
    SqlAlchemyEmailMessageRepository,
    SqlAlchemyReservaRepository,
)
from vivecaribe.infrastructure.integrations.gmail import GmailMailbox
from vivecaribe.infrastructure.integrations.outlook import OutlookMailbox
from vivecaribe.infrastructure.integrations.whatsapp import NoOpWhatsAppNotifier
from vivecaribe.logging import logger
from vivecaribe.settings import BookingProviderAccount

NEW_BOOKINGS_QUERY = "new_bookings_query"
MailboxClient = GmailMailbox | OutlookMailbox


class ProcessBookingEmailsUseCase:
    """Fetch booking emails for configured booking providers and persist reservas."""

    def __init__(
        self,
        *,
        accounts: list[BookingProviderAccount],
        email_messages: SqlAlchemyEmailMessageRepository,
        reservas: SqlAlchemyReservaRepository,
        whatsapp: NoOpWhatsAppNotifier,
        max_results: int = 30,
    ) -> None:
        """Wire booking-provider accounts, stores, and WhatsApp."""
        self._accounts = accounts
        self._email_messages = email_messages
        self._reservas = reservas
        self._whatsapp = whatsapp
        self._max_results = max_results
        self.fetched = 0
        self.created = 0
        self.existing = 0
        self.notified = 0

    async def get_messages_from_mailbox(
        self,
        account: BookingProviderAccount,
        query: str,
    ) -> list[EmailMessage]:
        """Fetch messages for ``query`` from the account's mailbox client."""
        mailbox = account.mailbox.client
        try:
            messages = await mailbox.fetch_messages(
                query=query,
                max_results=self._max_results,
            )
        except DomainError:
            logger.exception(
                "Fetch failed for booking_provider=%s",
                account.booking_provider,
            )
            return []
        return messages

    async def get_or_create_reserva_from_email_message(
        self,
        email_message: EmailMessage,
        booking_provider: BookingProvider,
    ) -> tuple[EmailMessage, Reserva, bool]:
        """Extract a draft from ``email_message`` and get_or_create the reserva.

        Returns:
            ``(stored_message, reserva, created)``
        """
        extractor_cls: type[BaseExtractor] = EXTRACTORS[booking_provider]
        draft = extractor_cls.from_html(email_message.body_html).to_draft()
        self._validate_draft(draft)

        stored_message, _ = await self._email_messages.get_or_create(email_message)
        reserva = draft.to_reserva(
            source=stored_message.source,
            sender=stored_message.sender,
            subject=stored_message.subject,
            fecha_email_recibido=stored_message.received_at,
            email_message_id=stored_message.id,
            notificado_whatsapp=False,
        )
        saved, created = await self._reservas.get_or_create(reserva)
        return stored_message, saved, created

    async def notify_if_necessary(
        self,
        stored_message: EmailMessage,
        reserva: Reserva,
        mailbox: MailboxClient,
    ) -> tuple[bool, Reserva]:
        """Notify via WhatsApp; mark message read only on a real send.

        Returns:
            ``(notified, reserva)`` — reserva may be updated if notified.
        """
        notified = await self._whatsapp.notify(reserva)
        if notified:
            reserva.notificado_whatsapp = True
            reserva = await self._reservas.save(reserva)
            await mailbox.mark_as_read(
                mailbox_message_id=stored_message.mailbox_message_id,
            )
            logger.info(
                "Marked message %s as read after WhatsApp notify",
                stored_message.mailbox_message_id,
            )
        else:
            logger.info(
                "Skipping mark_as_read for %s (WhatsApp not confirmed)",
                stored_message.mailbox_message_id,
            )
        return notified, reserva

    async def start(self) -> ProcessBookingEmailsUseCase:
        """Run the pipeline for every configured booking-provider account.

        Counters ``fetched``, ``created``, ``existing``, and ``notified``
        are reset at the start of each run.
        """
        self.fetched = 0
        self.created = 0
        self.existing = 0
        self.notified = 0

        for account in self._accounts:
            mailbox = account.mailbox.client
            query = account.mailbox.queries.get(NEW_BOOKINGS_QUERY, "")
            if not query:
                logger.error(
                    "Missing %s for booking_provider=%s",
                    NEW_BOOKINGS_QUERY,
                    account.booking_provider,
                )
                continue

            logger.info(
                "Fetching booking_provider=%s mailbox_name=%s query=%s",
                account.booking_provider,
                account.mailbox.mailbox_name,
                query,
            )
            messages = await self.get_messages_from_mailbox(account, query)
            self.fetched += len(messages)

            for message in messages:
                try:
                    stored_message, reserva, created = (
                        await self.get_or_create_reserva_from_email_message(
                            message,
                            account.booking_provider,
                        )
                    )
                    notified, _ = await self.notify_if_necessary(
                        stored_message,
                        reserva,
                        mailbox,
                    )
                except (ValidationError, DomainError) as exc:
                    logger.warning(
                        "Pipeline skipped %s/%s: %s",
                        account.booking_provider,
                        message.mailbox_message_id,
                        exc.message,
                    )
                    continue

                if created:
                    self.created += 1
                else:
                    self.existing += 1
                if notified:
                    self.notified += 1

        logger.info(
            "Pipeline done fetched=%s created=%s existing=%s notified=%s",
            self.fetched,
            self.created,
            self.existing,
            self.notified,
        )
        return self

    def _validate_draft(self, draft: ReservaDraft) -> None:
        """Enforce minimum booking invariants before persistence."""
        if not draft.reserva_reference.strip():
            raise ValidationError(
                "reserva_reference is required",
                field="reserva_reference",
            )
        if not draft.customer_name.strip():
            raise ValidationError(
                "customer_name is required",
                field="customer_name",
            )
        if not draft.nombre_experiencia.strip():
            raise ValidationError(
                "nombre_experiencia is required",
                field="nombre_experiencia",
            )
        if draft.price < 0:
            raise ValidationError("price must be >= 0", field="price")


async def _run_manually() -> None:
    """Wire dependencies from Settings/env and run one pipeline pass."""
    from vivecaribe.infrastructure.db.session import (
        create_engine,
        create_session_factory,
    )
    from vivecaribe.logging import configure_logging
    from vivecaribe.settings import get_settings

    settings = get_settings()
    configure_logging(settings)

    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    accounts = settings.load_booking_providers().booking_providers

    async with session_factory() as session:
        use_case = ProcessBookingEmailsUseCase(
            accounts=accounts,
            email_messages=SqlAlchemyEmailMessageRepository(session),
            reservas=SqlAlchemyReservaRepository(session),
            whatsapp=NoOpWhatsAppNotifier(),
        )
        await use_case.start()
        await session.commit()

    logger.info(
        "Manual run finished fetched=%s created=%s existing=%s notified=%s",
        use_case.fetched,
        use_case.created,
        use_case.existing,
        use_case.notified,
    )
    await engine.dispose()


if __name__ == "__main__":
    import asyncio

    asyncio.run(_run_manually())

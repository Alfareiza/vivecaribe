"""Unit tests for booking extractors and booking-email use case."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from vivecaribe.application.automation.models import ReservaDraft
from vivecaribe.application.automation.providers import (
    GetYourGuideExtractor,
    HomefansExtractor,
    PropioExtractor,
    ViatorExtractor,
)
from vivecaribe.application.automation.use_cases import ProcessBookingEmailsUseCase
from vivecaribe.domain.email_message import EmailMessage
from vivecaribe.domain.enums import BookingProvider, ReservaEstado
from vivecaribe.domain.errors import DomainError, ValidationError
from vivecaribe.infrastructure.integrations.whatsapp import NoOpWhatsAppNotifier
from vivecaribe.settings import BookingProviderAccount, MailboxConfig
from tests.fakes import (
    AlwaysNotifyWhatsApp,
    FakeEmailMessageStore,
    FakeMailbox,
    FakeReservaStore,
    FailingMailbox,
)

FIXTURES = Path(__file__).parent / "fixtures" / "emails"


def _message_from_fixture(
    filename: str,
    *,
    sender: str,
    source: str = "gmail",
) -> EmailMessage:
    """Load an HTML fixture into an ``EmailMessage``."""
    html = (FIXTURES / filename).read_text(encoding="utf-8")
    return EmailMessage(
        source=source,
        mailbox_message_id=f"ext-{filename}",
        sender=sender,
        recipients=["ops@vivecaribe.com"],
        subject=f"Booking {filename}",
        body_html=html,
        received_at=datetime(2026, 7, 8, 12, 0, tzinfo=UTC),
    )


def _account(
    *,
    booking_provider: BookingProvider,
    mailbox_name: str,
    credentials_vars: dict[str, str] | None = None,
    query: str,
) -> BookingProviderAccount:
    """Build a booking-provider account from mailbox config fields."""
    return BookingProviderAccount(
        booking_provider=booking_provider,
        mailbox=MailboxConfig(
            mailbox_name=mailbox_name,  # type: ignore[arg-type]
            credentials_vars=credentials_vars or {},
            queries={"new_bookings_query": query},
        ),
    )


def _bind_mailbox(monkeypatch: pytest.MonkeyPatch, mailbox: FakeMailbox) -> None:
    """Point ``MailboxConfig.client`` at a fake mailbox for the test."""
    monkeypatch.setattr(
        MailboxConfig,
        "client",
        property(lambda self, m=mailbox: m),
    )


def test_getyourguide_extractor_from_fixture() -> None:
    """GYG HTML sample yields booking fields via getters."""
    html = (FIXTURES / "getyourguide.html").read_text(encoding="utf-8")
    ext = GetYourGuideExtractor.from_html(html)

    assert ext.get_reserva_reference() == "GYGX7NG8ARBW"
    assert "Football Match" in ext.get_nombre_experiencia()
    assert ext.get_ciudad_evento() == "Cartagena"
    assert ext.get_participants() == 2
    assert ext.get_customer_name() == "Terrance Turner"
    assert ext.get_phone() == "+16625709162"
    assert ext.get_pais_del_visitante() == "US"
    assert ext.get_moneda() == "USD"
    assert ext.get_price() == Decimal("186.00")
    assert ext.get_income() == Decimal("130.200")
    assert ext.get_dt_evento() == datetime(2026, 5, 2, 15, 25, tzinfo=UTC)

    draft = ext.to_draft()
    assert draft.booking_provider == BookingProvider.GETYOURGUIDE
    assert draft.price == Decimal("186.00")
    assert draft.income == Decimal("130.200")


def test_homefans_extractor_from_fixture() -> None:
    """Homefans HTML sample yields booking fields via getters."""
    html = (FIXTURES / "homefans.html").read_text(encoding="utf-8")
    ext = HomefansExtractor.from_html(html)

    assert ext.get_reserva_reference() == "48295"
    assert "Match Day Experience" in ext.get_nombre_experiencia()
    assert ext.get_customer_name() == "Vincent Roeleveld"
    assert ext.get_participants() == 1
    assert ext.get_moneda() == "EUR"
    assert ext.get_price() == Decimal("89.68")
    assert ext.get_income() == Decimal("63.7500")
    assert ext.get_pais_del_visitante() == "NL"
    assert ext.get_phone() == "+31641428471"
    assert ext.get_dt_evento() == datetime(2026, 7, 29, 17, 4, tzinfo=UTC)


def test_viator_extractor_from_fixture() -> None:
    """Real Viator confirmation HTML maps onto draft fields."""
    html = (FIXTURES / "viator.html").read_text(encoding="utf-8")
    ext = ViatorExtractor.from_html(html)

    assert ext.get_reserva_reference() == "BR-1429496135"
    assert (
        ext.get_nombre_experiencia()
        == "Soccer at the Metropolitan stadium with local fans"
    )
    assert ext.get_ciudad_evento() == "Barranquilla"
    assert ext.get_dt_evento() == datetime(2026, 8, 1, tzinfo=UTC)
    assert ext.get_participants() == 1
    assert ext.get_customer_name() == "Jane Doe"
    assert ext.get_phone() == "+18137350000"
    assert ext.get_pais_del_visitante() == "US"
    assert ext.get_moneda() == "USD"
    assert ext.get_price() == Decimal("102.7040")
    assert ext.get_income() == Decimal("78.40")
    assert ext.get_estado().value == "confirmada"


def test_propio_extractor_from_fixture() -> None:
    """Propio WooCommerce HTML sample yields booking fields via getters."""
    html = (FIXTURES / "propio.html").read_text(encoding="utf-8")
    ext = PropioExtractor.from_html(html)

    assert ext.get_reserva_reference() == "1995"
    assert ext.get_nombre_experiencia() == "Watch Junior de Barranquilla Match"
    assert ext.get_ciudad_evento() == "Barranquilla"
    assert ext.get_dt_evento() == datetime(2026, 8, 1, 12, 40, tzinfo=UTC)
    assert ext.get_participants() == 2
    assert ext.get_customer_name() == "Lara Oliveira"
    assert ext.get_phone() == "+64224550339"
    assert ext.get_pais_del_visitante() == "NZ"
    assert ext.get_moneda() == "USD"
    assert ext.get_price() == Decimal("190.00")
    assert ext.get_income() == Decimal("190.00")
    assert ext.get_estado() == ReservaEstado.CONFIRMADA

    draft = ext.to_draft()
    assert draft.booking_provider == BookingProvider.PROPIO
    assert draft.income == draft.price


def test_propio_ciudad_missing_from_title_returns_empty(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """City falls back to empty string and logs when title has no known city."""
    html = """
    <h1>New order: #1</h1>
    <div class="email-introduction"><p>new order from Ada:</p></div>
    <tr class="order_item"><td><h3>Watch Junior Match</h3>
    <p>Trip Date: <strong>August 1, 2026 12:40 pm</strong></p>
    <p>Guest x <strong>1</strong></p></td></tr>
    <th>Total:</th><td><span class="woocommerce-Price-amount">$10.00</span></td>
    """
    ext = PropioExtractor.from_html(html)
    with caplog.at_level("WARNING"):
        assert ext.get_ciudad_evento() == ""
    assert "ciudad_experiencia not found" in caplog.text


@pytest.mark.asyncio
async def test_pipeline_happy_path_noop_whatsapp_skips_mark_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Persist reserva; NoOp WhatsApp ⇒ notificado false, no mark_as_read."""
    message = _message_from_fixture(
        "getyourguide.html",
        sender="noreply@getyourguide.com",
    )
    mailbox = FakeMailbox([message])
    _bind_mailbox(monkeypatch, mailbox)
    reservas = FakeReservaStore()
    use_case = ProcessBookingEmailsUseCase(
        accounts=[
            _account(
                booking_provider=BookingProvider.GETYOURGUIDE,
                mailbox_name="gmail",
                query="from:getyourguide.com",
            ),
        ],
        email_messages=FakeEmailMessageStore(),  # type: ignore[arg-type]
        reservas=reservas,  # type: ignore[arg-type]
        whatsapp=NoOpWhatsAppNotifier(),
    )

    await use_case.start()

    assert use_case.fetched == 1
    assert use_case.created == 1
    assert use_case.existing == 0
    assert use_case.notified == 0
    assert mailbox.marked_read == []
    stored = next(iter(reservas.by_key.values()))
    assert stored.notificado_whatsapp is False
    assert stored.price == Decimal("186.00")
    assert stored.income == Decimal("130.200")


@pytest.mark.asyncio
async def test_pipeline_notify_true_with_noop_still_skips_mark_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``notify=True`` with NoOp still leaves messages unread."""
    message = _message_from_fixture(
        "getyourguide.html",
        sender="noreply@getyourguide.com",
    )
    mailbox = FakeMailbox([message])
    _bind_mailbox(monkeypatch, mailbox)
    use_case = ProcessBookingEmailsUseCase(
        accounts=[
            _account(
                booking_provider=BookingProvider.GETYOURGUIDE,
                mailbox_name="gmail",
                query="from:getyourguide.com",
            ),
        ],
        email_messages=FakeEmailMessageStore(),  # type: ignore[arg-type]
        reservas=FakeReservaStore(),  # type: ignore[arg-type]
        whatsapp=NoOpWhatsAppNotifier(),
    )

    await use_case.start(notify=True)

    assert use_case.notified == 0
    assert mailbox.marked_read == []


@pytest.mark.asyncio
async def test_pipeline_marks_read_only_when_whatsapp_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When notify returns True, message is marked read and flag flipped."""
    message = _message_from_fixture(
        "homefans.html",
        sender="orders@homefans.com",
        source="outlook",
    )
    mailbox = FakeMailbox([message])
    _bind_mailbox(monkeypatch, mailbox)
    reservas = FakeReservaStore()
    use_case = ProcessBookingEmailsUseCase(
        accounts=[
            _account(
                booking_provider=BookingProvider.HOMEFANS,
                mailbox_name="outlook",
                query="from:homefans.com",
            ),
        ],
        email_messages=FakeEmailMessageStore(),  # type: ignore[arg-type]
        reservas=reservas,  # type: ignore[arg-type]
        whatsapp=AlwaysNotifyWhatsApp(),
    )

    await use_case.start(notify=True)

    assert use_case.notified == 1
    assert mailbox.marked_read == [message.mailbox_message_id]
    stored = next(iter(reservas.by_key.values()))
    assert stored.notificado_whatsapp is True


@pytest.mark.asyncio
async def test_pipeline_skips_mark_read_when_mailbox_lacks_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Zoho-style mailboxes without ``mark_as_read`` still notify successfully."""

    class _NoMarkMailbox:
        """Mailbox client that only supports fetch."""

        def __init__(self, messages: list[EmailMessage]) -> None:
            self.messages = messages

        async def fetch_messages(
            self,
            *,
            query: str,
            max_results: int = 30,
        ) -> list[EmailMessage]:
            return self.messages[:max_results]

    message = _message_from_fixture(
        "propio.html",
        sender="orders@grupovivecaribe.com",
        source="zoho",
    )
    mailbox = _NoMarkMailbox([message])
    monkeypatch.setattr(
        MailboxConfig,
        "client",
        property(lambda self, m=mailbox: m),
    )
    use_case = ProcessBookingEmailsUseCase(
        accounts=[
            _account(
                booking_provider=BookingProvider.PROPIO,
                mailbox_name="zoho",
                query="You've got a new order",
            ),
        ],
        email_messages=FakeEmailMessageStore(),  # type: ignore[arg-type]
        reservas=FakeReservaStore(),  # type: ignore[arg-type]
        whatsapp=AlwaysNotifyWhatsApp(),
    )

    await use_case.start(notify=True)

    assert use_case.notified == 1
    assert use_case.created == 1


@pytest.mark.asyncio
async def test_pipeline_error_path_extraction_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A message that doesn't match its booking HTML shape is skipped."""
    message = EmailMessage(
        source="gmail",
        mailbox_message_id="unknown-1",
        sender="random@example.com",
        subject="Hello",
        body_html="<p>no booking here</p>",
        received_at=datetime.now(UTC),
    )
    _bind_mailbox(monkeypatch, FakeMailbox([message]))
    use_case = ProcessBookingEmailsUseCase(
        accounts=[
            _account(
                booking_provider=BookingProvider.GETYOURGUIDE,
                mailbox_name="gmail",
                query="anything",
            ),
        ],
        email_messages=FakeEmailMessageStore(),  # type: ignore[arg-type]
        reservas=FakeReservaStore(),  # type: ignore[arg-type]
        whatsapp=NoOpWhatsAppNotifier(),
    )

    await use_case.start()

    assert use_case.fetched == 1
    assert use_case.created == 0


@pytest.mark.asyncio
async def test_pipeline_skips_account_without_query() -> None:
    """An account missing ``new_bookings_query`` is skipped entirely."""
    use_case = ProcessBookingEmailsUseCase(
        accounts=[
            _account(
                booking_provider=BookingProvider.VIATOR,
                mailbox_name="gmail",
                query="",
            ),
        ],
        email_messages=FakeEmailMessageStore(),  # type: ignore[arg-type]
        reservas=FakeReservaStore(),  # type: ignore[arg-type]
        whatsapp=NoOpWhatsAppNotifier(),
    )

    await use_case.start()

    assert use_case.fetched == 0
    assert use_case.created == 0


@pytest.mark.asyncio
async def test_pipeline_filters_by_booking_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``booking_provider`` filter processes only the matching account."""
    message = _message_from_fixture(
        "getyourguide.html",
        sender="noreply@getyourguide.com",
    )
    mailbox = FakeMailbox([message])
    _bind_mailbox(monkeypatch, mailbox)
    use_case = ProcessBookingEmailsUseCase(
        accounts=[
            _account(
                booking_provider=BookingProvider.GETYOURGUIDE,
                mailbox_name="gmail",
                query="from:gyg",
            ),
            _account(
                booking_provider=BookingProvider.VIATOR,
                mailbox_name="gmail",
                query="from:viator",
            ),
        ],
        email_messages=FakeEmailMessageStore(),  # type: ignore[arg-type]
        reservas=FakeReservaStore(),  # type: ignore[arg-type]
        whatsapp=NoOpWhatsAppNotifier(),
    )

    await use_case.start(booking_provider=BookingProvider.GETYOURGUIDE)

    assert use_case.fetched == 1
    assert use_case.created == 1


@pytest.mark.asyncio
async def test_pipeline_second_run_counts_existing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reprocessing the same booking increments ``existing``, not ``created``."""
    message = _message_from_fixture(
        "getyourguide.html",
        sender="noreply@getyourguide.com",
    )
    mailbox = FakeMailbox([message])
    _bind_mailbox(monkeypatch, mailbox)
    email_messages = FakeEmailMessageStore()
    reservas = FakeReservaStore()
    accounts = [
        _account(
            booking_provider=BookingProvider.GETYOURGUIDE,
            mailbox_name="gmail",
            query="from:gyg",
        ),
    ]
    first = ProcessBookingEmailsUseCase(
        accounts=accounts,
        email_messages=email_messages,  # type: ignore[arg-type]
        reservas=reservas,  # type: ignore[arg-type]
        whatsapp=NoOpWhatsAppNotifier(),
    )
    second = ProcessBookingEmailsUseCase(
        accounts=accounts,
        email_messages=email_messages,  # type: ignore[arg-type]
        reservas=reservas,  # type: ignore[arg-type]
        whatsapp=NoOpWhatsAppNotifier(),
    )

    await first.start()
    await second.start()

    assert first.created == 1
    assert second.created == 0
    assert second.existing == 1


@pytest.mark.asyncio
async def test_get_messages_from_mailbox_swallows_domain_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fetch DomainError returns an empty list and does not crash the run."""
    _bind_mailbox(monkeypatch, FailingMailbox(DomainError("mailbox down")))
    use_case = ProcessBookingEmailsUseCase(
        accounts=[
            _account(
                booking_provider=BookingProvider.GETYOURGUIDE,
                mailbox_name="gmail",
                query="from:gyg",
            ),
        ],
        email_messages=FakeEmailMessageStore(),  # type: ignore[arg-type]
        reservas=FakeReservaStore(),  # type: ignore[arg-type]
        whatsapp=NoOpWhatsAppNotifier(),
    )

    await use_case.start()

    assert use_case.fetched == 0
    assert use_case.created == 0


def test_validate_draft_rejects_invalid_fields() -> None:
    """``_validate_draft`` enforces required fields and non-negative price."""
    use_case = ProcessBookingEmailsUseCase(
        accounts=[],
        email_messages=FakeEmailMessageStore(),  # type: ignore[arg-type]
        reservas=FakeReservaStore(),  # type: ignore[arg-type]
        whatsapp=NoOpWhatsAppNotifier(),
    )
    base = ReservaDraft(
        booking_provider=BookingProvider.VIATOR,
        reserva_reference="VT-1",
        estado=ReservaEstado.CONFIRMADA,
        nombre_experiencia="Tour",
        ciudad_experiencia="Cartagena",
        participants=1,
        customer_name="Ada",
        price=Decimal("10.00"),
        income=Decimal("8.00"),
    )

    with pytest.raises(ValidationError, match="reserva_reference"):
        use_case._validate_draft(base.model_copy(update={"reserva_reference": "  "}))
    with pytest.raises(ValidationError, match="customer_name"):
        use_case._validate_draft(base.model_copy(update={"customer_name": ""}))
    with pytest.raises(ValidationError, match="nombre_experiencia"):
        use_case._validate_draft(base.model_copy(update={"nombre_experiencia": ""}))
    with pytest.raises(ValidationError, match="price"):
        use_case._validate_draft(base.model_copy(update={"price": Decimal("-1")}))


def test_reserva_draft_to_reserva() -> None:
    """Draft maps cleanly onto domain Reserva."""
    draft = ReservaDraft(
        booking_provider=BookingProvider.VIATOR,
        reserva_reference="VT-1",
        estado=ReservaEstado.CONFIRMADA,
        nombre_experiencia="Tour",
        ciudad_experiencia="Cartagena",
        participants=1,
        customer_name="Ada",
        price=Decimal("10.00"),
        income=Decimal("8.00"),
    )
    message_id = uuid4()
    reserva = draft.to_reserva(
        source="gmail",
        sender="x@viator.com",
        subject="Booking",
        fecha_email_recibido=datetime(2026, 1, 1, tzinfo=UTC),
        email_message_id=message_id,
    )
    assert reserva.email_message_id == message_id
    assert reserva.booking_provider == BookingProvider.VIATOR
    assert reserva.reserva_reference == "VT-1"
    assert reserva.income == Decimal("8.00")
    assert reserva.notificado_whatsapp is False

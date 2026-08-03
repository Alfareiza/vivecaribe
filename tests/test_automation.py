"""Unit tests for booking extractors and booking-email use case."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock
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
from vivecaribe.domain.errors import ValidationError
from vivecaribe.domain.reserva import Reserva
from vivecaribe.infrastructure.integrations.whatsapp import NoOpWhatsAppNotifier
from vivecaribe.settings import BookingProviderAccount, MailboxConfig

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
    credentials_file: str,
    query: str,
) -> BookingProviderAccount:
    """Build a booking-provider account from mailbox config fields."""
    return BookingProviderAccount(
        booking_provider=booking_provider,
        mailbox=MailboxConfig(
            mailbox_name=mailbox_name,  # type: ignore[arg-type]
            credentials_file=credentials_file,
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
    assert ext.get_moneda() == "USD"
    assert ext.get_price() == Decimal("186.00")
    assert ext.get_income() == Decimal("186.00")
    assert ext.get_dt_evento() == datetime(2026, 5, 2, 15, 25, tzinfo=UTC)

    draft = ext.to_draft()
    assert draft.booking_provider == BookingProvider.GETYOURGUIDE
    assert draft.income == draft.price


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
    assert ext.get_income() == Decimal("89.68")
    assert ext.get_pais_del_visitante() == "Netherlands"
    assert ext.get_phone() == "0031641428471"
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
    assert ext.get_price() == Decimal("78.40")
    assert ext.get_income() == Decimal("78.40")
    assert ext.get_estado().value == "confirmada"


def test_propio_extractor_is_skeleton() -> None:
    """Propio remains a skeleton until a sample HTML exists."""
    ext = PropioExtractor.from_html("<p>propio booking</p>")
    with pytest.raises(ValidationError, match="skeleton"):
        ext.get_customer_name()


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
                credentials_file="vivecaribe_token.json",
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
    assert stored.income == stored.price


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
                credentials_file="homefans_outlook_token.txt",
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
                credentials_file="vivecaribe_token.json",
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
                credentials_file="vivecaribe_token.json",
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


def test_mailbox_config_client_builds_gmail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``MailboxConfig.client`` builds ``GmailMailbox`` from a local secrets file."""
    from vivecaribe.infrastructure.integrations.gmail import GmailMailbox
    import vivecaribe.settings as settings_mod

    monkeypatch.setattr(settings_mod, "MAILBOX_CREDENTIALS_DIR", tmp_path)
    token_path = tmp_path / "vivecaribe_token.json"
    token_path.write_text(
        '{"token": "x", "refresh_token": "y", "token_uri": "https://oauth2.googleapis.com/token",'
        ' "client_id": "id", "client_secret": "secret"}',
        encoding="utf-8",
    )
    config = MailboxConfig(
        mailbox_name="gmail",
        credentials_file="vivecaribe_token.json",
        queries={"new_bookings_query": "x"},
    )
    assert isinstance(config.client, GmailMailbox)
    assert config.credentials_path == token_path
    assert config.client._credentials_path == token_path


def test_gmail_credentials_env_name_mapping() -> None:
    """Token filenames map to the Vercel env var names already in use."""
    from vivecaribe.settings import gmail_credentials_env_name

    assert (
        gmail_credentials_env_name("vivecaribe_token.json")
        == "VIVECARIBE_GMAIL_TOKEN_JSON"
    )
    assert (
        gmail_credentials_env_name("footballtourcol_token.json")
        == "FOOTBALLTOURCOL_GMAIL_TOKEN_JSON"
    )


def test_mailbox_config_falls_back_to_env_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without a secrets file, ``client`` loads JSON from the derived env var."""
    from vivecaribe.infrastructure.integrations.gmail import GmailMailbox
    import vivecaribe.settings as settings_mod

    monkeypatch.setattr(settings_mod, "MAILBOX_CREDENTIALS_DIR", tmp_path)
    monkeypatch.setenv(
        "VIVECARIBE_GMAIL_TOKEN_JSON",
        '{"token": "x", "refresh_token": "y", "token_uri": "https://oauth2.googleapis.com/token", "client_id": "id", "client_secret": "secret"}',
    )
    config = MailboxConfig(
        mailbox_name="gmail",
        credentials_file="vivecaribe_token.json",
        queries={"new_bookings_query": "x"},
    )
    assert isinstance(config.client, GmailMailbox)
    assert config.client._credentials_json is not None


def test_gmail_refreshes_on_first_token_load_even_if_creds_look_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stale token+future expiry must still refresh (avoids Gmail HTTP 401)."""
    from vivecaribe.infrastructure.integrations.gmail import GmailMailbox

    mailbox = GmailMailbox(credentials_json='{"token":"stale"}')
    fake_creds = MagicMock()
    fake_creds.refresh_token = "refresh"
    fake_creds.valid = True
    fake_creds.expired = False
    fake_creds.token = "fresh-token"

    monkeypatch.setattr(mailbox, "_load_credentials", lambda: fake_creds)

    def _fake_refresh(_request: object) -> None:
        fake_creds.token = "fresh-token"

    fake_creds.refresh.side_effect = _fake_refresh

    assert mailbox._require_token() == "fresh-token"
    fake_creds.refresh.assert_called_once()


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

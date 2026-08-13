"""Unit tests for the business domain core."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from vivecaribe.domain import (
    BookingProvider,
    ConflictError,
    DomainError,
    EmailMessage,
    MeetingPoint,
    NotFoundError,
    Reserva,
    ReservaEstado,
    TipoTour,
    User,
    ValidationError,
    compute_paid_at,
)


def _sample_reserva(**overrides: object) -> Reserva:
    """Build a minimal valid ``Reserva`` for tests."""
    data: dict[str, object] = {
        "source": "gmail",
        "booking_provider": BookingProvider.GETYOURGUIDE,
        "reserva_reference": "msg-123",
        "sender": "bookings@getyourguide.com",
        "estado": ReservaEstado.EN_PROGRESO,
        "subject": "New booking",
        "fecha_email_recibido": datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
        "nombre_experiencia": "City Tour",
        "ciudad_experiencia": "Cartagena",
        "fecha_evento": datetime(2026, 8, 15, 9, 0, tzinfo=UTC),
        "participants": 2,
        "customer_name": "Ada Lovelace",
        "phone": "+573001112233",
        "pais_del_visitante": "CO",
        "moneda": "USD",
        "price": Decimal("120.50"),
        "income": Decimal("96.40"),
        "notificado_whatsapp": False,
        "email_message_id": uuid4(),
        "user_id": None,
    }
    data.update(overrides)
    return Reserva.model_validate(data)


def test_booking_provider_values() -> None:
    """``BookingProvider`` exposes the four booking channels."""
    assert set(BookingProvider) == {
        BookingProvider.GETYOURGUIDE,
        BookingProvider.VIATOR,
        BookingProvider.HOMEFANS,
        BookingProvider.PROPIO,
    }
    assert BookingProvider.VIATOR.value == "viator"


def test_reserva_estado_includes_flow_states() -> None:
    """Lifecycle enum covers persist/notify and error outcomes."""
    assert ReservaEstado.EN_PROGRESO.value == "en_progreso"
    assert ReservaEstado.ERROR.value == "error"
    assert ReservaEstado.CONFIRMADA in ReservaEstado
    assert ReservaEstado.CANCELADA in ReservaEstado


def test_reserva_to_dict_serializes_enums_decimals_and_uuids() -> None:
    """``Reserva.to_dict`` produces JSON-friendly primitive values."""
    email_message_id = uuid4()
    reserva = _sample_reserva(
        email_message_id=email_message_id,
        price=Decimal("10.00"),
        income=Decimal("8.00"),
    )

    data = reserva.to_dict()

    assert data["booking_provider"] == "getyourguide"
    assert data["estado"] == "en_progreso"
    assert data["price"] == "10.00"
    assert data["income"] == "8.00"
    assert data["email_message_id"] == str(email_message_id)
    assert data["reserva_reference"] == "msg-123"
    assert isinstance(UUID(str(data["id"])), UUID)
    assert data["fecha_email_recibido"] == "2026-07-01T12:00:00Z"
    assert data["notificado_whatsapp"] is False


def test_user_to_dict() -> None:
    """``User.to_dict`` includes identity and password hash fields."""
    user = User(email="ops@vivecaribe.com", password_hash="hashed")

    data = user.to_dict()

    assert data["email"] == "ops@vivecaribe.com"
    assert data["password_hash"] == "hashed"
    assert data["is_active"] is True
    assert isinstance(UUID(str(data["id"])), UUID)


def test_domain_error_hierarchy() -> None:
    """Domain errors expose message metadata for API mapping later."""
    missing = NotFoundError("missing", entity="User")
    invalid = ValidationError("required", field="email")
    conflict = ConflictError("duplicate")

    assert isinstance(missing, DomainError)
    assert missing.entity == "User"
    assert "User" in str(missing)
    assert invalid.field == "email"
    assert "email" in str(invalid)
    assert isinstance(conflict, DomainError)
    assert DomainError().message == "Domain error"


def test_email_message_defaults() -> None:
    """``EmailMessage`` fills optional fields with safe defaults."""
    message = EmailMessage(
        source="gmail",
        mailbox_message_id="m1",
        sender="a@b.com",
        received_at=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
    )
    assert message.recipients == []
    assert message.subject == ""
    assert message.body_html == ""
    assert message.metadata == {}
    assert isinstance(message.id, UUID)


def test_tipo_tour_and_meeting_point_literal_values() -> None:
    """New enums keep human-readable wire values."""
    assert TipoTour.FOOTBALL_TOUR.value == "football tour"
    assert TipoTour.CITY_TOUR.value == "city tour"
    assert MeetingPoint.OLD_SHOES_MONUMENT.value == "old shoes monument"
    assert MeetingPoint.DOOR_TO_DOOR.value == "Door-to-Door"


def test_compute_paid_at_none_without_fecha_evento() -> None:
    """Missing event date yields no payout date."""
    assert compute_paid_at(BookingProvider.GETYOURGUIDE, None) is None


def test_compute_paid_at_gyg_weekday_seventh() -> None:
    """GYG: 7th of next month when that day is Mon–Fri."""
    # 15 Aug 2026 → 7 Sep 2026 (Monday)
    paid = compute_paid_at(
        BookingProvider.GETYOURGUIDE,
        datetime(2026, 8, 15, 9, 0),
    )
    assert paid is not None
    assert paid.date().isoformat() == "2026-09-07"


def test_compute_paid_at_viator_saturday_seventh_uses_ninth() -> None:
    """Viator: when the 7th is Saturday, payout is the 9th."""
    # 15 Jan 2026 → 7 Feb 2026 (Saturday) → 9 Feb
    paid = compute_paid_at(
        BookingProvider.VIATOR,
        datetime(2026, 1, 15, 12, 0),
    )
    assert paid is not None
    assert paid.date().isoformat() == "2026-02-09"


def test_compute_paid_at_gyg_sunday_seventh_uses_ninth() -> None:
    """GYG: when the 7th is Sunday, payout is the 9th."""
    # 15 May 2026 → 7 Jun 2026 (Sunday) → 9 Jun
    paid = compute_paid_at(
        BookingProvider.GETYOURGUIDE,
        datetime(2026, 5, 15, 12, 0),
    )
    assert paid is not None
    assert paid.date().isoformat() == "2026-06-09"


def test_compute_paid_at_gyg_december_rolls_to_january() -> None:
    """GYG December events pay out in January of the next year."""
    paid = compute_paid_at(
        BookingProvider.GETYOURGUIDE,
        datetime(2026, 12, 20, 12, 0),
    )
    assert paid is not None
    # 7 Jan 2027 is Thursday
    assert paid.date().isoformat() == "2027-01-07"


def test_compute_paid_at_propio_next_day() -> None:
    """Propio pays the calendar day after the event."""
    paid = compute_paid_at(
        BookingProvider.PROPIO,
        datetime(2026, 8, 15, 9, 0),
    )
    assert paid is not None
    assert paid.date().isoformat() == "2026-08-16"


def test_compute_paid_at_homefans_next_thursday() -> None:
    """Homefans: next Thursday after a non-Thursday event."""
    # Saturday 15 Aug 2026 → Thursday 20 Aug 2026
    paid = compute_paid_at(
        BookingProvider.HOMEFANS,
        datetime(2026, 8, 15, 9, 0),
    )
    assert paid is not None
    assert paid.date().isoformat() == "2026-08-20"


def test_compute_paid_at_homefans_on_thursday_skips_to_next_week() -> None:
    """Homefans: event on Thursday → Thursday of the following week."""
    # Thursday 13 Aug 2026 → Thursday 20 Aug 2026
    paid = compute_paid_at(
        BookingProvider.HOMEFANS,
        datetime(2026, 8, 13, 9, 0),
    )
    assert paid is not None
    assert paid.date().isoformat() == "2026-08-20"


def test_reserva_operator_field_defaults() -> None:
    """New operator fields default to null / false; ``paid_at`` is derived."""
    reserva = _sample_reserva(fecha_evento=None)
    assert reserva.notas_cliente is None
    assert reserva.tipo_tour is None
    assert reserva.meeting_point is None
    assert reserva.menores_de_edad is False
    assert reserva.paid_at is None
    assert reserva.costos is None


def test_reserva_derives_paid_at_on_construction() -> None:
    """``Reserva(...)`` syncs ``paid_at`` from provider + ``fecha_evento``."""
    reserva = _sample_reserva(
        booking_provider=BookingProvider.GETYOURGUIDE,
        fecha_evento=datetime(2026, 8, 15, 9, 0, tzinfo=UTC),
        paid_at=datetime(2000, 1, 1, tzinfo=UTC),  # ignored / overwritten
    )
    assert reserva.paid_at is not None
    assert reserva.paid_at.date().isoformat() == "2026-09-07"


def test_reserva_model_copy_recomputes_paid_at() -> None:
    """``model_copy`` re-validates so ``paid_at`` tracks provider/event changes."""
    reserva = _sample_reserva(
        booking_provider=BookingProvider.GETYOURGUIDE,
        fecha_evento=datetime(2026, 8, 15, 9, 0, tzinfo=UTC),
    )
    updated = reserva.model_copy(
        update={"booking_provider": BookingProvider.PROPIO},
    )
    assert updated.paid_at is not None
    assert updated.paid_at.date().isoformat() == "2026-08-16"

    cleared = updated.model_copy(update={"fecha_evento": None})
    assert cleared.paid_at is None


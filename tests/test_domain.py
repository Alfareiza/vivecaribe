"""Unit tests for the business domain core."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from vivecaribe.domain import (
    BookingProvider,
    DomainError,
    NotFoundError,
    Reserva,
    ReservaEstado,
    User,
    ValidationError,
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

    assert isinstance(missing, DomainError)
    assert missing.entity == "User"
    assert "User" in str(missing)
    assert invalid.field == "email"
    assert "email" in str(invalid)

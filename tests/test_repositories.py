"""Integration tests for SQLAlchemy repositories (needs vivecaribe_test)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from vivecaribe.domain.email_message import EmailMessage
from vivecaribe.domain.enums import BookingProvider, ReservaEstado
from vivecaribe.domain.reserva import Reserva
from vivecaribe.domain.user import User
from vivecaribe.infrastructure.db.repositories import (
    SqlAlchemyEmailMessageRepository,
    SqlAlchemyReservaRepository,
    SqlAlchemyUserRepository,
)


@pytest.mark.asyncio
async def test_user_save_and_get_by_email(db_session: AsyncSession) -> None:
    """Users round-trip through the repository."""
    repo = SqlAlchemyUserRepository(db_session)
    user = User(email="ops@vivecaribe.com", password_hash="hashed")

    saved = await repo.save(user)
    found = await repo.get_by_email("ops@vivecaribe.com")

    assert found is not None
    assert found.id == saved.id
    assert found.email == "ops@vivecaribe.com"


@pytest.mark.asyncio
async def test_reserva_get_or_create_is_idempotent(db_session: AsyncSession) -> None:
    """``get_or_create`` is idempotent on ``(booking_provider, reserva_reference)``."""
    user_repo = SqlAlchemyUserRepository(db_session)
    email_message_repo = SqlAlchemyEmailMessageRepository(db_session)
    reserva_repo = SqlAlchemyReservaRepository(db_session)

    user = await user_repo.save(
        User(email="guide@vivecaribe.com", password_hash="hashed"),
    )
    email_message = await email_message_repo.save(
        EmailMessage(
            source="gmail",
            mailbox_message_id="ext-1",
            sender="bookings@getyourguide.com",
            recipients=["ops@vivecaribe.com"],
            subject="New booking",
            body_text="plain",
            body_html="<p>html</p>",
            received_at=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
            metadata={"label": "gyg"},
        ),
    )

    draft = Reserva(
        source="gmail",
        booking_provider=BookingProvider.GETYOURGUIDE,
        reserva_reference="msg-idempotent-1",
        sender="bookings@getyourguide.com",
        estado=ReservaEstado.EN_PROGRESO,
        subject="New booking",
        fecha_email_recibido=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
        nombre_experiencia="City Tour",
        ciudad_experiencia="Cartagena",
        fecha_evento=datetime(2026, 8, 15, 9, 0, tzinfo=UTC),
        participants=2,
        customer_name="Ada Lovelace",
        phone="+573001112233",
        pais_del_visitante="CO",
        moneda="USD",
        price=Decimal("120.50"),
        income=Decimal("96.40"),
        email_message_id=email_message.id,
        user_id=user.id,
    )

    first, created_first = await reserva_repo.get_or_create(draft)
    second, created_second = await reserva_repo.get_or_create(
        draft.model_copy(update={"id": uuid4(), "customer_name": "Other"}),
    )

    assert created_first is True
    assert created_second is False
    assert first.id == second.id
    assert second.customer_name == "Ada Lovelace"
    assert second.user_id == user.id
    assert second.to_dict()["booking_provider"] == "getyourguide"

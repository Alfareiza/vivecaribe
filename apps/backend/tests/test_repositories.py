"""Integration tests for SQLAlchemy repositories (needs vivecaribe_test)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from vivecaribe.domain.email_message import EmailMessage
from vivecaribe.domain.enums import (
    BookingProvider,
    Campeonato,
    Ciudad,
    Estadio,
    ReservaEstado,
)
from vivecaribe.domain.partido import Partido
from vivecaribe.domain.reserva import Reserva
from vivecaribe.domain.user import User
from vivecaribe.infrastructure.db.repositories import (
    SqlAlchemyEmailMessageRepository,
    SqlAlchemyPartidoRepository,
    SqlAlchemyReservaRepository,
    SqlAlchemyUserRepository,
)


def _partido(**overrides: object) -> Partido:
    """Build a valid ``Partido`` with sensible defaults."""
    defaults: dict[str, object] = {
        "equipo_local": "Junior",
        "equipo_visitante": "Millonarios",
        "nombre_campeonato": Campeonato.COLOMBIAN_LEAGUE,
        "estadio": Estadio.METROPOLITANO,
        "fecha": datetime(2026, 9, 1, 20, 0, tzinfo=UTC),
        "ciudad": Ciudad.BARRANQUILLA,
    }
    defaults.update(overrides)
    return Partido(**defaults)  # type: ignore[arg-type]


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

    by_id = await reserva_repo.get_by_id(first.id)
    assert by_id is not None
    assert by_id.reserva_reference == "msg-idempotent-1"

    first.customer_name = "Updated Name"
    updated = await reserva_repo.save(first)
    assert updated.customer_name == "Updated Name"

    items, total = await reserva_repo.list(skip=0, limit=10)
    assert total == 1
    assert items[0].id == first.id
    assert items[0].customer_name == "Updated Name"

    assert await reserva_repo.soft_delete(first.id) is True
    assert await reserva_repo.get_by_id(first.id) is None
    items_after, total_after = await reserva_repo.list(skip=0, limit=10)
    assert total_after == 0
    assert items_after == []
    assert await reserva_repo.soft_delete(first.id) is False


@pytest.mark.asyncio
async def test_email_message_get_or_create_is_idempotent(
    db_session: AsyncSession,
) -> None:
    """Email messages are idempotent on ``(source, mailbox_message_id)``."""
    repo = SqlAlchemyEmailMessageRepository(db_session)
    message = EmailMessage(
        source="gmail",
        mailbox_message_id="ext-email-1",
        sender="bookings@getyourguide.com",
        recipients=["ops@vivecaribe.com"],
        subject="New booking",
        body_text="plain",
        body_html="<p>html</p>",
        received_at=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
        metadata={"label": "gyg"},
    )

    first, created_first = await repo.get_or_create(message)
    second, created_second = await repo.get_or_create(
        message.model_copy(update={"id": uuid4(), "subject": "Other"}),
    )

    assert created_first is True
    assert created_second is False
    assert first.id == second.id
    assert second.subject == "New booking"
    assert second.metadata == {"label": "gyg"}

    by_id = await repo.get_by_id(first.id)
    assert by_id is not None
    assert by_id.mailbox_message_id == "ext-email-1"

    first.subject = "Updated subject"
    saved = await repo.save(first)
    assert saved.subject == "Updated subject"


@pytest.mark.asyncio
async def test_user_get_by_id_and_save_update(db_session: AsyncSession) -> None:
    """Users can be loaded by id and updated in place."""
    repo = SqlAlchemyUserRepository(db_session)
    saved = await repo.save(User(email="guide@vivecaribe.com", password_hash="hashed"))
    found = await repo.get_by_id(saved.id)
    assert found is not None
    assert found.email == "guide@vivecaribe.com"

    saved.is_active = False
    updated = await repo.save(saved)
    assert updated.is_active is False
    assert await repo.get_by_id(uuid4()) is None


@pytest.mark.asyncio
async def test_partido_find_partidos_based_on_ciudad_and_dt_matches_by_bogota_day_and_ciudad(
    db_session: AsyncSession,
) -> None:
    """``find_partidos_based_on_ciudad_and_dt`` matches ciudad (case-insensitive) and Bogota calendar day.

    ``partido.fecha`` is 2026-09-01 21:00 Bogota (2026-09-02 02:00 UTC) — a
    different UTC calendar day than the reserva's, so an exact-day compare
    without timezone conversion would wrongly miss it.
    """
    repo = SqlAlchemyPartidoRepository(db_session)
    matching = await repo.save(
        _partido(fecha=datetime(2026, 9, 2, 2, 0, tzinfo=UTC)),
    )
    await repo.save(
        _partido(equipo_local="Other", ciudad=Ciudad.CARTAGENA),
    )
    await repo.save(
        _partido(equipo_local="Different day", fecha=datetime(2026, 9, 5, 20, 0, tzinfo=UTC)),
    )

    fecha_evento = datetime(2026, 9, 1, 18, 0, tzinfo=UTC)  # 13:00 Bogota, same day
    matches = await repo.find_partidos_based_on_ciudad_and_dt("barranquilla", fecha_evento)

    assert [m.id for m in matches] == [matching.id]


@pytest.mark.asyncio
async def test_partido_find_partidos_based_on_ciudad_and_dt_returns_multiple_on_ambiguous_day(
    db_session: AsyncSession,
) -> None:
    """Two partidos in the same city/day both come back — caller decides."""
    repo = SqlAlchemyPartidoRepository(db_session)
    fecha = datetime(2026, 9, 1, 20, 0, tzinfo=UTC)
    first = await repo.save(_partido(fecha=fecha))
    second = await repo.save(_partido(equipo_local="Other", fecha=fecha))

    matches = await repo.find_partidos_based_on_ciudad_and_dt("Barranquilla", fecha)

    assert {m.id for m in matches} == {first.id, second.id}


@pytest.mark.asyncio
async def test_partido_find_partidos_based_on_ciudad_and_dt_no_match_returns_empty(
    db_session: AsyncSession,
) -> None:
    """No candidates in that city/day returns an empty list."""
    repo = SqlAlchemyPartidoRepository(db_session)
    await repo.save(_partido())

    matches = await repo.find_partidos_based_on_ciudad_and_dt("Cartagena", datetime(2026, 9, 1, 20, 0, tzinfo=UTC))

    assert matches == []

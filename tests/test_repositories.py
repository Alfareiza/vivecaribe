"""Integration tests for SQLAlchemy repositories (needs local Postgres)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from vivecaribe.domain.email_message import EmailMessage
from vivecaribe.domain.enums import BookingProvider, ReservaEstado
from vivecaribe.domain.reserva import Reserva
from vivecaribe.domain.user import User
from vivecaribe.infrastructure.db.models import Base
from vivecaribe.infrastructure.db.repositories import (
    SqlAlchemyEmailMessageRepository,
    SqlAlchemyReservaRepository,
    SqlAlchemyUserRepository,
)
from vivecaribe.infrastructure.db.session import create_engine
from vivecaribe.settings import get_settings


async def _postgres_available(engine: AsyncEngine) -> bool:
    """Return ``True`` if the engine can connect to Postgres."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    """Create a disposable async engine for repository tests."""
    eng = create_engine(get_settings())
    if not await _postgres_available(eng):
        await eng.dispose()
        pytest.skip("Postgres is not available (start with: docker compose up -d db)")

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield eng

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Yield a committed session bound to the test engine."""
    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with factory() as session:
        yield session
        await session.commit()


@pytest.mark.asyncio
async def test_user_save_and_get_by_email(session: AsyncSession) -> None:
    """Users round-trip through the repository."""
    repo = SqlAlchemyUserRepository(session)
    user = User(email="ops@vivecaribe.com", password_hash="hashed")

    saved = await repo.save(user)
    found = await repo.get_by_email("ops@vivecaribe.com")

    assert found is not None
    assert found.id == saved.id
    assert found.email == "ops@vivecaribe.com"


@pytest.mark.asyncio
async def test_reserva_get_or_create_is_idempotent(session: AsyncSession) -> None:
    """``get_or_create`` is idempotent on ``(booking_provider, reserva_reference)``."""
    user_repo = SqlAlchemyUserRepository(session)
    email_message_repo = SqlAlchemyEmailMessageRepository(session)
    reserva_repo = SqlAlchemyReservaRepository(session)

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

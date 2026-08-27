"""Integration tests for dashboard report aggregations."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from vivecaribe.domain.enums import (
    BookingProvider,
    Campeonato,
    Ciudad,
    Estadio,
    ReservaEstado,
)
from vivecaribe.domain.partido import Partido
from vivecaribe.domain.reserva import Reserva
from vivecaribe.infrastructure.db.models import ReservaORM
from vivecaribe.infrastructure.db.repositories import (
    SqlAlchemyPartidoRepository,
    SqlAlchemyReservaRepository,
)
from vivecaribe.infrastructure.db.reports_repository import SqlAlchemyReportsRepository


def _partido(**overrides: object) -> Partido:
    defaults: dict[str, object] = {
        "equipo_local": "Junior",
        "equipo_visitante": "Millonarios",
        "nombre_campeonato": Campeonato.COLOMBIAN_LEAGUE,
        "estadio": Estadio.METROPOLITANO,
        "fecha": datetime(2099, 6, 15, 20, 0, tzinfo=UTC),
        "ciudad": Ciudad.BARRANQUILLA,
    }
    defaults.update(overrides)
    return Partido(**defaults)  # type: ignore[arg-type]


def _reserva(**overrides: object) -> Reserva:
    defaults: dict[str, object] = {
        "source": "manual",
        "booking_provider": BookingProvider.GETYOURGUIDE,
        "reserva_reference": f"RPT-{uuid4()}",
        "sender": None,
        "estado": ReservaEstado.CONFIRMADA,
        "subject": None,
        "fecha_email_recibido": None,
        "nombre_experiencia": "Football tour",
        "ciudad_experiencia": "Barranquilla",
        "fecha_evento": datetime(2026, 8, 15, 17, 0, tzinfo=UTC),
        "participants": 2,
        "customer_name": "Ada Lovelace",
        "phone": "+573001112233",
        "pais_del_visitante": "US",
        "moneda": "COP",
        "price": Decimal("100000.00"),
        "income": Decimal("100000.00"),
    }
    defaults.update(overrides)
    return Reserva(**defaults)  # type: ignore[arg-type]


async def _persist_reserva(
    session: AsyncSession,
    reserva: Reserva,
    *,
    income_final: Decimal | None = None,
    costos: Decimal | None = None,
) -> Reserva:
    """Save a reserva and optionally set derived finance fields on the ORM row."""
    repo = SqlAlchemyReservaRepository(session)
    saved = await repo.save(reserva)
    if income_final is not None or costos is not None:
        row = await session.get(ReservaORM, saved.id)
        assert row is not None
        if income_final is not None:
            row.income_final = income_final
        if costos is not None:
            row.costos = costos
        await session.flush()
        await session.refresh(row)
        saved = Reserva.model_validate(row)
    return saved


@pytest.mark.asyncio
async def test_get_summary_counts_only_confirmed_non_deleted_reservas(
    db_session: AsyncSession,
) -> None:
    """Summary KPIs include confirmada rows and ignore other states."""
    reports = SqlAlchemyReportsRepository(db_session)
    partido_repo = SqlAlchemyPartidoRepository(db_session)
    partido = await partido_repo.save(_partido())

    await _persist_reserva(
        db_session,
        _reserva(
            participants=3,
            partido_id=partido.id,
            booking_provider=BookingProvider.GETYOURGUIDE,
        ),
        income_final=Decimal("100000.00"),
        costos=Decimal("20000.00"),
    )
    await _persist_reserva(
        db_session,
        _reserva(
            participants=5,
            booking_provider=BookingProvider.VIATOR,
            estado=ReservaEstado.EN_PROGRESO,
        ),
        income_final=Decimal("50000.00"),
        costos=Decimal("10000.00"),
    )
    cancelled = await _persist_reserva(
        db_session,
        _reserva(participants=9, estado=ReservaEstado.CANCELADA),
        income_final=Decimal("80000.00"),
        costos=Decimal("5000.00"),
    )
    deleted = await _persist_reserva(
        db_session,
        _reserva(participants=4),
        income_final=Decimal("70000.00"),
        costos=Decimal("3000.00"),
    )
    reserva_repo = SqlAlchemyReservaRepository(db_session)
    await reserva_repo.soft_delete(deleted.id)
    assert cancelled.estado is ReservaEstado.CANCELADA

    summary = await reports.get_summary()

    assert summary.participants == 3
    assert summary.reservas == 1
    assert summary.profit == Decimal("80000.00")
    assert summary.partidos == 1


@pytest.mark.asyncio
async def test_get_summary_excludes_null_costos_from_profit(
    db_session: AsyncSession,
) -> None:
    """Profit sums only rows where both income_final and costos are set."""
    reports = SqlAlchemyReportsRepository(db_session)

    await _persist_reserva(
        db_session,
        _reserva(participants=2),
        income_final=Decimal("100000.00"),
        costos=Decimal("25000.00"),
    )
    await _persist_reserva(
        db_session,
        _reserva(participants=4),
        income_final=Decimal("50000.00"),
        costos=None,
    )

    summary = await reports.get_summary()

    assert summary.participants == 6
    assert summary.reservas == 2
    assert summary.profit == Decimal("75000.00")


@pytest.mark.asyncio
async def test_get_summary_filters_by_provider_and_bogota_date(
    db_session: AsyncSession,
) -> None:
    """Optional provider and fecha filters compose with AND semantics."""
    reports = SqlAlchemyReportsRepository(db_session)

    await _persist_reserva(
        db_session,
        _reserva(
            booking_provider=BookingProvider.GETYOURGUIDE,
            fecha_evento=datetime(2026, 9, 1, 4, 30, tzinfo=UTC),
            participants=2,
        ),
        income_final=Decimal("100000.00"),
        costos=Decimal("10000.00"),
    )
    await _persist_reserva(
        db_session,
        _reserva(
            booking_provider=BookingProvider.VIATOR,
            fecha_evento=datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
            participants=5,
        ),
        income_final=Decimal("200000.00"),
        costos=Decimal("20000.00"),
    )

    by_provider = await reports.get_summary(
        booking_provider=BookingProvider.GETYOURGUIDE,
    )
    assert by_provider.reservas == 1
    assert by_provider.participants == 2

    # 2026-09-01T04:30:00Z is still 2026-08-31 in Bogota.
    by_date = await reports.get_summary(
        fecha_from=date(2026, 8, 31),
        fecha_to=date(2026, 8, 31),
    )
    assert by_date.reservas == 1
    assert by_date.participants == 2


@pytest.mark.asyncio
async def test_get_statistics_groups_income_and_costos_by_month(
    db_session: AsyncSession,
) -> None:
    """Statistics returns monthly income_final and costos totals."""
    reports = SqlAlchemyReportsRepository(db_session)

    await _persist_reserva(
        db_session,
        _reserva(fecha_evento=datetime(2026, 7, 10, 17, 0, tzinfo=UTC)),
        income_final=Decimal("100000.00"),
        costos=Decimal("10000.00"),
    )
    await _persist_reserva(
        db_session,
        _reserva(fecha_evento=datetime(2026, 7, 20, 17, 0, tzinfo=UTC)),
        income_final=Decimal("50000.00"),
        costos=Decimal("5000.00"),
    )
    await _persist_reserva(
        db_session,
        _reserva(fecha_evento=datetime(2026, 8, 5, 17, 0, tzinfo=UTC)),
        income_final=Decimal("80000.00"),
        costos=None,
    )

    stats = await reports.get_statistics()

    assert len(stats) == 2
    assert stats[0].month == date(2026, 7, 1)
    assert stats[0].income_final == Decimal("150000.00")
    assert stats[0].costos == Decimal("15000.00")
    assert stats[1].month == date(2026, 8, 1)
    assert stats[1].income_final == Decimal("80000.00")
    assert stats[1].costos == Decimal("0")


@pytest.mark.asyncio
async def test_get_monthly_sales_sums_profit_only_for_profitable_rows(
    db_session: AsyncSession,
) -> None:
    """Monthly sales excludes reservas missing costos."""
    reports = SqlAlchemyReportsRepository(db_session)

    await _persist_reserva(
        db_session,
        _reserva(fecha_evento=datetime(2026, 6, 1, 17, 0, tzinfo=UTC)),
        income_final=Decimal("100000.00"),
        costos=Decimal("30000.00"),
    )
    await _persist_reserva(
        db_session,
        _reserva(fecha_evento=datetime(2026, 6, 15, 17, 0, tzinfo=UTC)),
        income_final=Decimal("50000.00"),
        costos=None,
    )

    sales = await reports.get_monthly_sales()

    assert len(sales) == 1
    assert sales[0].month == date(2026, 6, 1)
    assert sales[0].profit == Decimal("70000.00")


@pytest.mark.asyncio
async def test_get_top_providers_ranks_by_profit_desc(
    db_session: AsyncSession,
) -> None:
    """Top providers orders channels by total profit."""
    reports = SqlAlchemyReportsRepository(db_session)

    await _persist_reserva(
        db_session,
        _reserva(booking_provider=BookingProvider.GETYOURGUIDE, participants=2),
        income_final=Decimal("100000.00"),
        costos=Decimal("20000.00"),
    )
    await _persist_reserva(
        db_session,
        _reserva(booking_provider=BookingProvider.VIATOR, participants=3),
        income_final=Decimal("200000.00"),
        costos=Decimal("50000.00"),
    )

    top = await reports.get_top_providers(limit=10)

    assert len(top) == 2
    assert top[0].provider is BookingProvider.VIATOR
    assert top[0].profit == Decimal("150000.00")
    assert top[0].reservas == 1
    assert top[0].participants == 3
    assert top[1].provider is BookingProvider.GETYOURGUIDE
    assert top[1].profit == Decimal("80000.00")


@pytest.mark.asyncio
async def test_get_top_cities_groups_on_ciudad_experiencia(
    db_session: AsyncSession,
) -> None:
    """Top cities aggregates profit by experience city."""
    reports = SqlAlchemyReportsRepository(db_session)

    await _persist_reserva(
        db_session,
        _reserva(ciudad_experiencia="Barranquilla"),
        income_final=Decimal("120000.00"),
        costos=Decimal("20000.00"),
    )
    await _persist_reserva(
        db_session,
        _reserva(ciudad_experiencia="Cartagena"),
        income_final=Decimal("90000.00"),
        costos=Decimal("10000.00"),
    )

    top = await reports.get_top_cities(limit=10)

    assert len(top) == 2
    assert top[0].city == "Barranquilla"
    assert top[0].profit == Decimal("100000.00")
    assert top[0].reservas == 1
    assert top[1].city == "Cartagena"
    assert top[1].profit == Decimal("80000.00")


@pytest.mark.asyncio
async def test_get_temporada_groups_participants_by_month_and_city(
    db_session: AsyncSession,
) -> None:
    """Temporada sums participants per month per city; skips non-confirmada."""
    reports = SqlAlchemyReportsRepository(db_session)

    await _persist_reserva(
        db_session,
        _reserva(
            ciudad_experiencia="Barranquilla",
            fecha_evento=datetime(2026, 7, 10, 17, 0, tzinfo=UTC),
            participants=2,
        ),
    )
    await _persist_reserva(
        db_session,
        _reserva(
            ciudad_experiencia="Barranquilla",
            fecha_evento=datetime(2026, 7, 20, 17, 0, tzinfo=UTC),
            participants=3,
        ),
    )
    await _persist_reserva(
        db_session,
        _reserva(
            ciudad_experiencia="Cartagena",
            fecha_evento=datetime(2026, 7, 15, 17, 0, tzinfo=UTC),
            participants=4,
        ),
    )
    await _persist_reserva(
        db_session,
        _reserva(
            ciudad_experiencia="Cartagena",
            fecha_evento=datetime(2026, 8, 5, 17, 0, tzinfo=UTC),
            participants=1,
        ),
    )
    await _persist_reserva(
        db_session,
        _reserva(
            estado=ReservaEstado.EN_PROGRESO,
            ciudad_experiencia="Barranquilla",
            fecha_evento=datetime(2026, 7, 12, 17, 0, tzinfo=UTC),
            participants=10,
        ),
    )

    points = await reports.get_temporada()

    assert [(point.month, point.city, point.participants) for point in points] == [
        (date(2026, 7, 1), "Barranquilla", 5),
        (date(2026, 7, 1), "Cartagena", 4),
        (date(2026, 8, 1), "Cartagena", 1),
    ]


@pytest.mark.asyncio
async def test_get_demographics_ranks_countries_by_participants(
    db_session: AsyncSession,
) -> None:
    """Demographics includes all confirmed reservas, not only profitable ones."""
    reports = SqlAlchemyReportsRepository(db_session)

    await _persist_reserva(
        db_session,
        _reserva(pais_del_visitante="US", participants=5),
        income_final=Decimal("100000.00"),
        costos=None,
    )
    await _persist_reserva(
        db_session,
        _reserva(pais_del_visitante="FR", participants=2),
        income_final=Decimal("50000.00"),
        costos=Decimal("10000.00"),
    )

    demo = await reports.get_demographics(limit=10)

    assert len(demo) == 2
    assert demo[0].country == "US"
    assert demo[0].participants == 5
    assert demo[0].reservas == 1
    assert demo[1].country == "FR"
    assert demo[1].participants == 2


@pytest.mark.asyncio
async def test_get_providers_returns_all_providers_with_data(
    db_session: AsyncSession,
) -> None:
    """Provider cards include every channel that has profitable reservas."""
    reports = SqlAlchemyReportsRepository(db_session)

    await _persist_reserva(
        db_session,
        _reserva(booking_provider=BookingProvider.PROPIO, participants=1),
        income_final=Decimal("50000.00"),
        costos=Decimal("5000.00"),
    )
    await _persist_reserva(
        db_session,
        _reserva(booking_provider=BookingProvider.AIRBNB, participants=4),
        income_final=Decimal("80000.00"),
        costos=Decimal("10000.00"),
    )

    providers = await reports.get_providers()

    assert len(providers) == 2
    assert providers[0].provider is BookingProvider.AIRBNB
    assert providers[0].profit == Decimal("70000.00")
    assert providers[1].provider is BookingProvider.PROPIO


@pytest.mark.asyncio
async def test_get_proximos_partidos_returns_future_matches_with_counts(
    db_session: AsyncSession,
) -> None:
    """Upcoming partidos include confirmed reserva/participant counts only."""
    reports = SqlAlchemyReportsRepository(db_session)
    partido_repo = SqlAlchemyPartidoRepository(db_session)
    future = await partido_repo.save(
        _partido(
            equipo_local="Junior",
            equipo_visitante="Nacional",
            fecha=datetime.now(UTC) + timedelta(days=30),
        ),
    )
    past = await partido_repo.save(
        _partido(
            equipo_local="Past",
            equipo_visitante="Old",
            fecha=datetime.now(UTC) - timedelta(days=1),
        ),
    )

    await _persist_reserva(
        db_session,
        _reserva(partido_id=future.id, participants=3),
        income_final=Decimal("100000.00"),
        costos=Decimal("10000.00"),
    )
    await _persist_reserva(
        db_session,
        _reserva(
            partido_id=future.id,
            participants=5,
            estado=ReservaEstado.CANCELADA,
        ),
        income_final=Decimal("50000.00"),
        costos=Decimal("5000.00"),
    )
    await _persist_reserva(
        db_session,
        _reserva(partido_id=past.id, participants=9),
        income_final=Decimal("50000.00"),
        costos=Decimal("5000.00"),
    )

    proximos = await reports.get_proximos_partidos(limit=5)

    assert len(proximos) == 1
    assert proximos[0].id == future.id
    assert proximos[0].equipo_local == "Junior"
    assert proximos[0].equipo_visitante == "Nacional"
    assert proximos[0].reservas_count == 1
    assert proximos[0].participants_count == 3


@pytest.mark.asyncio
async def test_get_proximos_partidos_includes_zero_count_partidos(
    db_session: AsyncSession,
) -> None:
    """A future partido with no confirmed reservas still appears with zero counts."""
    reports = SqlAlchemyReportsRepository(db_session)
    partido_repo = SqlAlchemyPartidoRepository(db_session)
    lonely = await partido_repo.save(
        _partido(
            equipo_local="Solo",
            equipo_visitante="Match",
            fecha=datetime.now(UTC) + timedelta(days=10),
        ),
    )

    proximos = await reports.get_proximos_partidos(limit=5)

    assert len(proximos) == 1
    assert proximos[0].id == lonely.id
    assert proximos[0].reservas_count == 0
    assert proximos[0].participants_count == 0

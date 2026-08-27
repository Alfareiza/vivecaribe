"""SQLAlchemy queries for dashboard report endpoints.

Performance notes
-----------------
Every public method issues **one** SQL statement and maps rows in Python.
There is no ORM relationship traversal and therefore **no N+1** risk inside
this repository.

The dashboard frontend calls several endpoints in parallel (one round-trip
each). That is an API-layer trade-off (independent caching / simpler
endpoints), not an N+1 pattern.

Indexes already present on ``reservas`` that help these queries:

- ``ix_reservas_estado``
- ``ix_reservas_booking_provider``
- ``ix_reservas_fecha_evento``
- partial filter via ``deleted_at IS NULL`` ( btree index on ``deleted_at`` )

Date-range filters apply ``timezone('America/Bogota', fecha_evento)::date``,
which prevents a plain btree seek on ``fecha_evento`` unless a functional
index is added later. At current scale this is acceptable; if the table
grows large, consider ``CREATE INDEX … ON reservas ((timezone('America/Bogota', fecha_evento)::date))``.

``get_proximos_partidos`` mirrors the partidos list pattern: one
``LEFT JOIN`` + ``GROUP BY`` with ``COUNT``/``SUM`` in the SELECT — no
follow-up queries per partido.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, Date, and_, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import Label

from vivecaribe.domain.enums import (
    BookingProvider,
    Campeonato,
    Ciudad,
    Estadio,
    ReservaEstado,
)
from vivecaribe.domain.reports import (
    DemographicItem,
    MonthlySalesPoint,
    MonthlyStatisticsPoint,
    ProviderCardItem,
    ProximoPartidoItem,
    ReportSummary,
    TemporadaPoint,
    TopCityItem,
    TopProviderItem,
)
from vivecaribe.infrastructure.db.models import PartidoORM, ReservaORM


def _reserva_report_filters(
    *,
    fecha_from: date | None = None,
    fecha_to: date | None = None,
    booking_provider: BookingProvider | None = None,
) -> list[ColumnElement[bool]]:
    """Build shared WHERE clauses for confirmed, non-deleted reservas.

    All dashboard aggregations start from the same base predicate so filter
    semantics stay consistent across endpoints.

    Args:
        fecha_from: Inclusive lower bound on ``fecha_evento`` (America/Bogota
            calendar day). When set, rows with null ``fecha_evento`` are
            excluded.
        fecha_to: Inclusive upper bound on ``fecha_evento`` (America/Bogota
            calendar day).
        booking_provider: Restrict to a single booking channel.

    Returns:
        A list of SQLAlchemy boolean expressions to pass to ``and_()``.
    """
    filters: list[ColumnElement[bool]] = [
        ReservaORM.deleted_at.is_(None),
        ReservaORM.estado == ReservaEstado.CONFIRMADA.value,
    ]
    if booking_provider is not None:
        filters.append(ReservaORM.booking_provider == booking_provider.value)
    if fecha_from is not None or fecha_to is not None:
        filters.append(ReservaORM.fecha_evento.is_not(None))
        event_day = cast(
            func.timezone("America/Bogota", ReservaORM.fecha_evento),
            Date,
        )
        if fecha_from is not None:
            filters.append(event_day >= fecha_from)
        if fecha_to is not None:
            filters.append(event_day <= fecha_to)
    return filters


def _profit_expr() -> ColumnElement[Any]:
    """Return the per-row net-profit expression ``income_final - costos``.

    Callers must pair this with ``_profitable_reserva_clause()`` in the
    WHERE clause or inside ``.filter()`` on ``func.sum`` so rows with null
    ``costos`` or ``income_final`` are excluded from profit totals.
    """
    return ReservaORM.income_final - ReservaORM.costos


def _profitable_reserva_clause() -> ColumnElement[bool]:
    """Return a predicate that keeps only rows with computable profit."""
    return and_(
        ReservaORM.income_final.is_not(None),
        ReservaORM.costos.is_not(None),
    )


def _month_bucket(column: Any) -> Label[Any]:
    """Truncate a timestamptz column to the first day of its calendar month."""
    return func.date_trunc("month", column).label("month")


class SqlAlchemyReportsRepository:
    """Dashboard aggregations backed by PostgreSQL.

    Each method runs a single aggregate query against ``reservas`` (or a
    single join query for upcoming partidos). Results are mapped to Pydantic
    domain objects in memory — no lazy loads, no per-row database access.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Bind this repository to an open async session."""
        self._session = session

    async def get_summary(
        self,
        *,
        fecha_from: date | None = None,
        fecha_to: date | None = None,
        booking_provider: BookingProvider | None = None,
    ) -> ReportSummary:
        """Return the four dashboard KPI values in one aggregate query.

        Computes ``participants`` (sum), ``reservas`` (count), ``profit``
        (sum of ``income_final - costos`` excluding null costos), and
        ``partidos`` (count of distinct non-null ``partido_id`` values).

        Single ``SELECT`` with conditional aggregates — no N+1.
        """
        filters = _reserva_report_filters(
            fecha_from=fecha_from,
            fecha_to=fecha_to,
            booking_provider=booking_provider,
        )
        where_clause = and_(*filters)

        summary_result = await self._session.execute(
            select(
                func.coalesce(func.sum(ReservaORM.participants), 0).label(
                    "participants",
                ),
                func.count(ReservaORM.id).label("reservas"),
                func.coalesce(
                    func.sum(_profit_expr()).filter(_profitable_reserva_clause()),
                    Decimal(0),
                ).label("profit"),
                func.count(func.distinct(ReservaORM.partido_id)).filter(
                    ReservaORM.partido_id.is_not(None),
                ).label("partidos"),
            ).where(where_clause),
        )
        row = summary_result.one()
        return ReportSummary(
            participants=int(row.participants),
            reservas=int(row.reservas),
            profit=row.profit or Decimal(0),
            partidos=int(row.partidos),
        )

    async def get_statistics(
        self,
        *,
        fecha_from: date | None = None,
        fecha_to: date | None = None,
        booking_provider: BookingProvider | None = None,
    ) -> list[MonthlyStatisticsPoint]:
        """Return monthly ``income_final`` vs ``costos`` for the Statistics chart.

        Groups by ``date_trunc('month', fecha_evento)``. The costos aggregate
        uses a filtered ``func.sum`` so null costos contribute zero rather
        than nullifying the whole month.

        One grouped query; result cardinality equals number of months with
        data (typically small).
        """
        filters = _reserva_report_filters(
            fecha_from=fecha_from,
            fecha_to=fecha_to,
            booking_provider=booking_provider,
        )
        filters.append(ReservaORM.fecha_evento.is_not(None))
        where_clause = and_(*filters)
        month = _month_bucket(ReservaORM.fecha_evento)

        result = await self._session.execute(
            select(
                month,
                func.coalesce(func.sum(ReservaORM.income_final), Decimal(0)).label(
                    "income_final",
                ),
                func.coalesce(
                    func.sum(ReservaORM.costos).filter(
                        ReservaORM.costos.is_not(None),
                    ),
                    Decimal(0),
                ).label("costos"),
            )
            .where(where_clause)
            .group_by(month)
            .order_by(month.asc()),
        )
        return [
            MonthlyStatisticsPoint(
                month=row.month.date(),
                income_final=row.income_final,
                costos=row.costos,
            )
            for row in result.all()
        ]

    async def get_monthly_sales(
        self,
        *,
        fecha_from: date | None = None,
        fecha_to: date | None = None,
        booking_provider: BookingProvider | None = None,
    ) -> list[MonthlySalesPoint]:
        """Return monthly profit totals for the Monthly Sales bar chart.

        Only includes reservas where both ``income_final`` and ``costos`` are
        set. One grouped query ordered chronologically.
        """
        filters = _reserva_report_filters(
            fecha_from=fecha_from,
            fecha_to=fecha_to,
            booking_provider=booking_provider,
        )
        filters.extend(
            [
                ReservaORM.fecha_evento.is_not(None),
                _profitable_reserva_clause(),
            ],
        )
        where_clause = and_(*filters)
        month = _month_bucket(ReservaORM.fecha_evento)

        result = await self._session.execute(
            select(
                month,
                func.coalesce(func.sum(_profit_expr()), Decimal(0)).label("profit"),
            )
            .where(where_clause)
            .group_by(month)
            .order_by(month.asc()),
        )
        return [
            MonthlySalesPoint(month=row.month.date(), profit=row.profit)
            for row in result.all()
        ]

    async def get_top_providers(
        self,
        *,
        fecha_from: date | None = None,
        fecha_to: date | None = None,
        booking_provider: BookingProvider | None = None,
        limit: int = 10,
    ) -> list[TopProviderItem]:
        """Return booking providers ranked by total profit (descending).

        Aggregates profit, reserva count, and participant count per
        ``booking_provider`` in one query. ``LIMIT`` is applied in SQL so
        PostgreSQL can stop early after sorting the grouped result.
        """
        filters = _reserva_report_filters(
            fecha_from=fecha_from,
            fecha_to=fecha_to,
            booking_provider=booking_provider,
        )
        filters.append(_profitable_reserva_clause())
        where_clause = and_(*filters)

        result = await self._session.execute(
            select(
                ReservaORM.booking_provider,
                func.coalesce(func.sum(_profit_expr()), Decimal(0)).label("profit"),
                func.count(ReservaORM.id).label("reservas"),
                func.coalesce(func.sum(ReservaORM.participants), 0).label(
                    "participants",
                ),
            )
            .where(where_clause)
            .group_by(ReservaORM.booking_provider)
            .order_by(func.sum(_profit_expr()).desc())
            .limit(limit),
        )
        return [
            TopProviderItem(
                provider=BookingProvider(row.booking_provider),
                profit=row.profit,
                reservas=int(row.reservas),
                participants=int(row.participants),
            )
            for row in result.all()
        ]

    async def get_top_cities(
        self,
        *,
        fecha_from: date | None = None,
        fecha_to: date | None = None,
        booking_provider: BookingProvider | None = None,
        limit: int = 10,
    ) -> list[TopCityItem]:
        """Return experience cities ranked by total profit (descending).

        Groups on ``ciudad_experiencia``. Single grouped query with SQL
        ``LIMIT`` — at most ``limit`` rows returned.
        """
        filters = _reserva_report_filters(
            fecha_from=fecha_from,
            fecha_to=fecha_to,
            booking_provider=booking_provider,
        )
        filters.append(_profitable_reserva_clause())
        where_clause = and_(*filters)

        result = await self._session.execute(
            select(
                ReservaORM.ciudad_experiencia,
                func.coalesce(func.sum(_profit_expr()), Decimal(0)).label("profit"),
                func.count(ReservaORM.id).label("reservas"),
            )
            .where(where_clause)
            .group_by(ReservaORM.ciudad_experiencia)
            .order_by(func.sum(_profit_expr()).desc())
            .limit(limit),
        )
        return [
            TopCityItem(
                city=row.ciudad_experiencia,
                profit=row.profit,
                reservas=int(row.reservas),
            )
            for row in result.all()
        ]

    async def get_temporada(
        self,
        *,
        fecha_from: date | None = None,
        fecha_to: date | None = None,
        booking_provider: BookingProvider | None = None,
    ) -> list[TemporadaPoint]:
        """Return participants grouped by month and experience city.

        One grouped query. Includes all confirmed reservas (no costos
        requirement) so volume of visitors is visible even before profit
        is known. Ordered chronologically, then by city name.
        """
        filters = _reserva_report_filters(
            fecha_from=fecha_from,
            fecha_to=fecha_to,
            booking_provider=booking_provider,
        )
        filters.append(ReservaORM.fecha_evento.is_not(None))
        where_clause = and_(*filters)
        month = _month_bucket(ReservaORM.fecha_evento)

        result = await self._session.execute(
            select(
                month,
                ReservaORM.ciudad_experiencia,
                func.coalesce(func.sum(ReservaORM.participants), 0).label(
                    "participants",
                ),
            )
            .where(where_clause)
            .group_by(month, ReservaORM.ciudad_experiencia)
            .order_by(month.asc(), ReservaORM.ciudad_experiencia.asc()),
        )
        return [
            TemporadaPoint(
                month=row.month.date(),
                city=row.ciudad_experiencia,
                participants=int(row.participants),
            )
            for row in result.all()
        ]

    async def get_demographics(
        self,
        *,
        fecha_from: date | None = None,
        fecha_to: date | None = None,
        booking_provider: BookingProvider | None = None,
        limit: int = 10,
    ) -> list[DemographicItem]:
        """Return visitor countries ranked by total participants (descending).

        Groups on ``pais_del_visitante``. Unlike profit endpoints, this
        includes all confirmed reservas (no costos requirement). Single
        grouped query with SQL ``LIMIT``.
        """
        filters = _reserva_report_filters(
            fecha_from=fecha_from,
            fecha_to=fecha_to,
            booking_provider=booking_provider,
        )
        where_clause = and_(*filters)

        result = await self._session.execute(
            select(
                ReservaORM.pais_del_visitante,
                func.count(ReservaORM.id).label("reservas"),
                func.coalesce(func.sum(ReservaORM.participants), 0).label(
                    "participants",
                ),
            )
            .where(where_clause)
            .group_by(ReservaORM.pais_del_visitante)
            .order_by(func.sum(ReservaORM.participants).desc())
            .limit(limit),
        )
        return [
            DemographicItem(
                country=row.pais_del_visitante or "Desconocido",
                reservas=int(row.reservas),
                participants=int(row.participants),
            )
            for row in result.all()
        ]

    async def get_providers(
        self,
        *,
        fecha_from: date | None = None,
        fecha_to: date | None = None,
        booking_provider: BookingProvider | None = None,
    ) -> list[ProviderCardItem]:
        """Return per-provider card summaries for every provider with data.

        Same aggregate shape as ``get_top_providers`` but without a row limit
        (at most seven enum values). Still a single grouped query — not one
        query per provider.
        """
        filters = _reserva_report_filters(
            fecha_from=fecha_from,
            fecha_to=fecha_to,
            booking_provider=booking_provider,
        )
        filters.append(_profitable_reserva_clause())
        where_clause = and_(*filters)

        result = await self._session.execute(
            select(
                ReservaORM.booking_provider,
                func.coalesce(func.sum(_profit_expr()), Decimal(0)).label("profit"),
                func.count(ReservaORM.id).label("reservas"),
                func.coalesce(func.sum(ReservaORM.participants), 0).label(
                    "participants",
                ),
            )
            .where(where_clause)
            .group_by(ReservaORM.booking_provider)
            .order_by(func.sum(_profit_expr()).desc()),
        )
        return [
            ProviderCardItem(
                provider=BookingProvider(row.booking_provider),
                profit=row.profit,
                reservas=int(row.reservas),
                participants=int(row.participants),
            )
            for row in result.all()
        ]

    async def get_proximos_partidos(self, *, limit: int = 5) -> list[ProximoPartidoItem]:
        """Return the next upcoming partidos with reserva/participant counts.

        Ignores dashboard date/provider filters by design. Uses the same
        single-query pattern as ``SqlAlchemyPartidoRepository.list``:

        - ``LEFT JOIN`` reservas with confirmada + non-deleted predicates
          in the ``ON`` clause (so partidos with zero matching reservas
          still appear with count 0)
        - ``GROUP BY partidos.id`` with ``COUNT`` and ``SUM`` aggregates

        No N+1: counts are computed in SQL, not fetched per partido.
        """
        now = datetime.now(UTC)
        where_clause = and_(
            PartidoORM.deleted_at.is_(None),
            PartidoORM.fecha >= now,
        )

        result = await self._session.execute(
            select(
                PartidoORM,
                func.count(ReservaORM.id).label("reservas_count"),
                func.coalesce(func.sum(ReservaORM.participants), 0).label(
                    "participants_count",
                ),
            )
            .outerjoin(
                ReservaORM,
                and_(
                    ReservaORM.partido_id == PartidoORM.id,
                    ReservaORM.deleted_at.is_(None),
                    ReservaORM.estado == ReservaEstado.CONFIRMADA.value,
                ),
            )
            .where(where_clause)
            .group_by(PartidoORM.id)
            .order_by(PartidoORM.fecha.asc())
            .limit(limit),
        )
        items: list[ProximoPartidoItem] = []
        for row, reservas_count, participants_count in result.all():
            items.append(
                ProximoPartidoItem(
                    id=row.id,
                    equipo_local=row.equipo_local,
                    equipo_visitante=row.equipo_visitante,
                    nombre_campeonato=Campeonato(row.nombre_campeonato),
                    estadio=Estadio(row.estadio),
                    fecha=row.fecha,
                    ciudad=Ciudad(row.ciudad),
                    reservas_count=int(reservas_count),
                    participants_count=int(participants_count),
                ),
            )
        return items

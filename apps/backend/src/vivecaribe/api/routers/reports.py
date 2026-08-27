"""Dashboard report HTTP routes."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from vivecaribe.api.deps import CurrentUser, ReportsRepo
from vivecaribe.domain.enums import BookingProvider
from vivecaribe.domain.reports import (
    DemographicItem,
    MonthlySalesPoint,
    MonthlyStatisticsPoint,
    ProviderCardItem,
    ProximoPartidoItem,
    ReportSummary,
    TopCityItem,
    TopProviderItem,
)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary", response_model=ReportSummary)
async def report_summary(
    reports: ReportsRepo,
    _current_user: CurrentUser,
    fecha_from: Annotated[
        date | None,
        Query(description="Inclusive lower bound (America/Bogota calendar day)"),
    ] = None,
    fecha_to: Annotated[
        date | None,
        Query(description="Inclusive upper bound (America/Bogota calendar day)"),
    ] = None,
    booking_provider: Annotated[BookingProvider | None, Query()] = None,
) -> ReportSummary:
    """Return dashboard KPI cards."""
    return await reports.get_summary(
        fecha_from=fecha_from,
        fecha_to=fecha_to,
        booking_provider=booking_provider,
    )


@router.get("/statistics", response_model=list[MonthlyStatisticsPoint])
async def report_statistics(
    reports: ReportsRepo,
    _current_user: CurrentUser,
    fecha_from: Annotated[date | None, Query()] = None,
    fecha_to: Annotated[date | None, Query()] = None,
    booking_provider: Annotated[BookingProvider | None, Query()] = None,
) -> list[MonthlyStatisticsPoint]:
    """Return monthly income_final vs costos series."""
    return await reports.get_statistics(
        fecha_from=fecha_from,
        fecha_to=fecha_to,
        booking_provider=booking_provider,
    )


@router.get("/monthly-sales", response_model=list[MonthlySalesPoint])
async def report_monthly_sales(
    reports: ReportsRepo,
    _current_user: CurrentUser,
    fecha_from: Annotated[date | None, Query()] = None,
    fecha_to: Annotated[date | None, Query()] = None,
    booking_provider: Annotated[BookingProvider | None, Query()] = None,
) -> list[MonthlySalesPoint]:
    """Return monthly profit series."""
    return await reports.get_monthly_sales(
        fecha_from=fecha_from,
        fecha_to=fecha_to,
        booking_provider=booking_provider,
    )


@router.get("/top-providers", response_model=list[TopProviderItem])
async def report_top_providers(
    reports: ReportsRepo,
    _current_user: CurrentUser,
    fecha_from: Annotated[date | None, Query()] = None,
    fecha_to: Annotated[date | None, Query()] = None,
    booking_provider: Annotated[BookingProvider | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[TopProviderItem]:
    """Return booking providers ranked by profit."""
    return await reports.get_top_providers(
        fecha_from=fecha_from,
        fecha_to=fecha_to,
        booking_provider=booking_provider,
        limit=limit,
    )


@router.get("/top-cities", response_model=list[TopCityItem])
async def report_top_cities(
    reports: ReportsRepo,
    _current_user: CurrentUser,
    fecha_from: Annotated[date | None, Query()] = None,
    fecha_to: Annotated[date | None, Query()] = None,
    booking_provider: Annotated[BookingProvider | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[TopCityItem]:
    """Return experience cities ranked by profit."""
    return await reports.get_top_cities(
        fecha_from=fecha_from,
        fecha_to=fecha_to,
        booking_provider=booking_provider,
        limit=limit,
    )


@router.get("/demographics", response_model=list[DemographicItem])
async def report_demographics(
    reports: ReportsRepo,
    _current_user: CurrentUser,
    fecha_from: Annotated[date | None, Query()] = None,
    fecha_to: Annotated[date | None, Query()] = None,
    booking_provider: Annotated[BookingProvider | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[DemographicItem]:
    """Return visitor countries ranked by participants."""
    return await reports.get_demographics(
        fecha_from=fecha_from,
        fecha_to=fecha_to,
        booking_provider=booking_provider,
        limit=limit,
    )


@router.get("/providers", response_model=list[ProviderCardItem])
async def report_providers(
    reports: ReportsRepo,
    _current_user: CurrentUser,
    fecha_from: Annotated[date | None, Query()] = None,
    fecha_to: Annotated[date | None, Query()] = None,
    booking_provider: Annotated[BookingProvider | None, Query()] = None,
) -> list[ProviderCardItem]:
    """Return per-provider card summaries."""
    return await reports.get_providers(
        fecha_from=fecha_from,
        fecha_to=fecha_to,
        booking_provider=booking_provider,
    )


@router.get("/proximos-partidos", response_model=list[ProximoPartidoItem])
async def report_proximos_partidos(
    reports: ReportsRepo,
    _current_user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> list[ProximoPartidoItem]:
    """Return the next upcoming partidos (ignores dashboard filters)."""
    return await reports.get_proximos_partidos(limit=limit)

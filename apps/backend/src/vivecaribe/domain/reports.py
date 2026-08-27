"""Domain schemas for dashboard report endpoints."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from vivecaribe.domain.enums import BookingProvider, Campeonato, Ciudad, Estadio


class ReportSummary(BaseModel):
    """KPI cards for the dashboard header row."""

    participants: int
    reservas: int
    profit: Decimal
    partidos: int


class MonthlyStatisticsPoint(BaseModel):
    """One month in the Statistics chart."""

    month: date
    income_final: Decimal
    costos: Decimal


class MonthlySalesPoint(BaseModel):
    """One month in the Monthly Sales bar chart."""

    month: date
    profit: Decimal


class TopProviderItem(BaseModel):
    """Ranked booking provider by profit."""

    provider: BookingProvider
    profit: Decimal
    reservas: int
    participants: int


class TopCityItem(BaseModel):
    """Ranked experience city by profit."""

    city: str
    profit: Decimal
    reservas: int


class TemporadaPoint(BaseModel):
    """One city in one month for the Temporada grouped-bar chart."""

    month: date
    city: str
    participants: int


class DemographicItem(BaseModel):
    """Visitor country breakdown."""

    country: str
    reservas: int
    participants: int


class ProviderCardItem(BaseModel):
    """Per-provider summary card."""

    provider: BookingProvider
    profit: Decimal
    participants: int
    reservas: int


class ProximoPartidoItem(BaseModel):
    """Upcoming partido row for the dashboard."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    equipo_local: str
    equipo_visitante: str
    nombre_campeonato: Campeonato
    estadio: Estadio
    fecha: datetime
    ciudad: Ciudad
    reservas_count: int = 0
    participants_count: int = 0

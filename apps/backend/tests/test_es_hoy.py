"""Unit tests for America/Bogota ``es_hoy`` computation."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from vivecaribe.api.schemas.reservas import _es_hoy

BOGOTA = ZoneInfo("America/Bogota")
UTC = ZoneInfo("UTC")


def test_es_hoy_none_fecha_is_false() -> None:
    """Null event date is never today."""
    assert _es_hoy(None) is False


def test_es_hoy_same_bogota_calendar_day() -> None:
    """Aware UTC that still falls on Bogota today is true."""
    now = datetime(2026, 8, 11, 10, 0, tzinfo=BOGOTA)
    # 2026-08-11 05:00 UTC == 2026-08-11 00:00 Bogota
    event = datetime(2026, 8, 11, 5, 0, tzinfo=UTC)
    assert _es_hoy(event, now=now) is True


def test_es_hoy_false_when_previous_bogota_day() -> None:
    """UTC midnight can still be previous calendar day in Bogota."""
    now = datetime(2026, 8, 11, 10, 0, tzinfo=BOGOTA)
    # 2026-08-11 04:00 UTC == 2026-08-10 23:00 Bogota
    event = datetime(2026, 8, 11, 4, 0, tzinfo=UTC)
    assert _es_hoy(event, now=now) is False


def test_es_hoy_naive_treated_as_bogota() -> None:
    """Naive datetimes are interpreted as Bogota wall time."""
    now = datetime(2026, 8, 11, 15, 0, tzinfo=BOGOTA)
    event = datetime(2026, 8, 11, 9, 30)
    assert _es_hoy(event, now=now) is True

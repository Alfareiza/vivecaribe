"""Domain enums for bookings and reservation lifecycle."""

from __future__ import annotations

from enum import StrEnum


class BookingProvider(StrEnum):
    """Marketplace / channel that originated a booking."""

    GETYOURGUIDE = "getyourguide"
    VIATOR = "viator"
    HOMEFANS = "homefans"
    PROPIO = "propio"


class ReservaEstado(StrEnum):
    """Lifecycle state of a ``Reserva``.

    Used by persistence and the notify flow; automation maps extraction
    outcomes onto these values without owning the enum itself.
    """

    EN_PROGRESO = "en_progreso"
    CONFIRMADA = "confirmada"
    CANCELADA = "cancelada"
    ERROR = "error"

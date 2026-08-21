"""Domain enums for bookings and reservation lifecycle."""

from __future__ import annotations

from enum import StrEnum


class BookingProvider(StrEnum):
    """Marketplace / channel that originated a booking."""

    GETYOURGUIDE = "getyourguide"
    VIATOR = "viator"
    HOMEFANS = "homefans"
    PROPIO = "propio"
    VAYARA = "vayara"
    AIRBNB = "airbnb"
    OTRO = "otro"


class ReservaEstado(StrEnum):
    """Lifecycle state of a ``Reserva``.

    Used by persistence and the notify flow; automation maps extraction
    outcomes onto these values without owning the enum itself.
    """

    EN_PROGRESO = "en_progreso"
    CONFIRMADA = "confirmada"
    CANCELADA = "cancelada"
    ERROR = "error"


class TipoTour(StrEnum):
    """Kind of guided experience on a reservation."""

    FOOTBALL_TOUR = "football tour"
    CITY_TOUR = "city tour"
    OTRO = ""


class MeetingPoint(StrEnum):
    """Where the guest is met for the experience."""

    OLD_SHOES_MONUMENT = "old shoes monument"
    DOOR_TO_DOOR = "Door-to-Door"


class Campeonato(StrEnum):
    """Championship a ``Partido`` belongs to."""

    COLOMBIAN_CUP = "Colombian Cup"
    COLOMBIAN_LEAGUE = "Colombian League"
    COPA_LIBERTADORES = "Copa Libertadores"
    COPA_SUDAMERICANA = "Copa Sudamericana"
    COLOMBIAN_SECOND_DIVISION_LEAGUE = "Colombian Second Division League"


class Estadio(StrEnum):
    """Stadium where a ``Partido`` is played."""

    JAIME_MORON = "Jaime Morón"
    ROMELIO_MARTINEZ = "Romelio Martínez"
    METROPOLITANO = "Metropolitano"


class Ciudad(StrEnum):
    """City where a ``Partido`` is played.

    Registering a new city is a one-line addition here — the column is a
    plain ``VARCHAR`` (no DB-level enum), so no migration is needed.
    """

    BARRANQUILLA = "Barranquilla"
    CARTAGENA = "Cartagena"


class GastoCategoria(StrEnum):
    """Expense category for a ``Gasto`` tied to a ``Partido``.

    At most one ``Gasto`` exists per ``(partido_id, categoria)`` pair.
    Registering a new category is a one-line addition here — the column is
    a plain ``VARCHAR`` (no DB-level enum), so no migration is needed.
    """

    COMIDA_SNACKS = "Comida y/o Snacks"
    TRANSPORTE = "Transporte"
    BOLETAS = "Boletas"
    APOYOS = "Apoyos"
    OTROS = "Otros"

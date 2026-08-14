"""``Partido`` — football match a ``Reserva`` may optionally attach to."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from vivecaribe.domain.enums import Campeonato, Ciudad, Estadio


class Partido(BaseModel):
    """Football match tracked independently of reservations.

    A partido can have many reservas (one-to-many); the FK lives on
    ``Reserva.partido_id`` and is always optional in both directions.
    """

    model_config = ConfigDict(from_attributes=True, validate_assignment=True)

    equipo_local: str = Field(max_length=25)
    equipo_visitante: str = Field(max_length=25)
    nombre_campeonato: Campeonato
    estadio: Estadio
    fecha: datetime
    ciudad: Ciudad
    deleted_at: datetime | None = None
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

"""Request/response schemas for partido CRUD endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from vivecaribe.api.schemas.reservas import ReservaShortItem
from vivecaribe.domain.enums import Campeonato, Ciudad, Estadio
from vivecaribe.domain.partido import Partido


class PartidoCreate(BaseModel):
    """Payload for ``POST /partidos``."""

    equipo_local: str = Field(max_length=25)
    equipo_visitante: str = Field(max_length=25)
    nombre_campeonato: Campeonato
    estadio: Estadio
    fecha: datetime
    ciudad: Ciudad


class PartidoUpdate(BaseModel):
    """Partial payload for ``PATCH /partidos/{id}``.

    Identity and audit fields are intentionally omitted so they stay
    immutable through this endpoint.
    """

    equipo_local: str | None = Field(default=None, max_length=25)
    equipo_visitante: str | None = Field(default=None, max_length=25)
    nombre_campeonato: Campeonato | None = None
    estadio: Estadio | None = None
    fecha: datetime | None = None
    ciudad: Ciudad | None = None


class PartidoShortItem(BaseModel):
    """Slim partido row for ``GET /partidos`` grid cards, with reservas count.

    ``reservas_count`` is computed via LEFT JOIN + COUNT in the repository query
    (no N+1 queries). Frontend uses this to show the badge count.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    equipo_local: str
    equipo_visitante: str
    nombre_campeonato: Campeonato
    estadio: Estadio
    fecha: datetime
    ciudad: Ciudad
    reservas_count: int = 0


class PartidoResponse(Partido):
    """Public partido representation (detail / mutations).

    ``reservas`` lists the non-deleted reservations currently linked to this
    partido; it is informational only — associating/dissociating a reserva
    happens from the Reserva side.
    """

    deleted_at: datetime | None = Field(default=None, exclude=True)
    reservas: list[ReservaShortItem] = Field(default_factory=list)


class PartidoListResponse(BaseModel):
    """Paginated partido list."""

    total: int
    items: list[PartidoShortItem]

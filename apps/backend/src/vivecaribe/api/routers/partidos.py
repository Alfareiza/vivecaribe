"""Partido HTTP routes — thin wrappers over the repository."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from vivecaribe.api.deps import CurrentUser, GastoRepo, PartidoRepo, ReservaRepo
from vivecaribe.api.schemas.gastos import GastoItem
from vivecaribe.api.schemas.partidos import (
    PartidoCreate,
    PartidoListResponse,
    PartidoResponse,
    PartidoShortItem,
    PartidoUpdate,
)
from vivecaribe.api.schemas.reservas import ReservaShortItem
from vivecaribe.domain.partido import Partido

router = APIRouter(tags=["partidos"])


@router.post(
    "/partidos",
    response_model=PartidoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_partido(
    payload: PartidoCreate,
    partidos: PartidoRepo,
    reservas: ReservaRepo,
    gastos: GastoRepo,
    _current_user: CurrentUser,
) -> PartidoResponse:
    """Create a partido (JWT required)."""
    partido = Partido(**payload.model_dump())
    saved = await partidos.save(partido)
    linked = await reservas.list_by_partido(saved.id)
    registered = await gastos.list_by_partido(saved.id)
    return PartidoResponse(
        **saved.model_dump(),
        reservas=[ReservaShortItem.model_validate(item) for item in linked],
        gastos=[GastoItem.model_validate(item) for item in registered],
    )


@router.get("/partidos", response_model=PartidoListResponse)
async def list_partidos(
    partidos: PartidoRepo,
    _current_user: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ciudad: Annotated[str | None, Query()] = None,
    fecha_from: Annotated[
        datetime | None,
        Query(description="Inclusive lower bound"),
    ] = None,
    fecha_to: Annotated[
        datetime | None,
        Query(description="Inclusive upper bound"),
    ] = None,
    q: Annotated[
        str | None,
        Query(description="Search equipo_local, equipo_visitante, ciudad"),
    ] = None,
) -> PartidoListResponse:
    """Return a filtered, paginated list of partidos with reservas count (JWT required).

    Filters compose with AND. Omitted params mean no constraint. Ordered by
    ``fecha`` ascending (soonest first). Uses single LEFT JOIN query (no N+1).
    """
    items, total = await partidos.list(
        skip=skip,
        limit=limit,
        ciudad=ciudad,
        fecha_from=fecha_from,
        fecha_to=fecha_to,
        q=q,
    )
    return PartidoListResponse(
        total=total,
        items=[PartidoShortItem.model_validate(item) for item in items],
    )


@router.get("/partidos/{partido_id}", response_model=PartidoResponse)
async def get_partido(
    partido_id: UUID,
    partidos: PartidoRepo,
    reservas: ReservaRepo,
    gastos: GastoRepo,
    _current_user: CurrentUser,
) -> PartidoResponse:
    """Return a single partido by id, with its linked reservas (JWT required)."""
    partido = await partidos.get_by_id(partido_id)
    if partido is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Partido {partido_id} not found",
        )
    linked = await reservas.list_by_partido(partido.id)
    registered = await gastos.list_by_partido(partido.id)
    return PartidoResponse(
        **partido.model_dump(),
        reservas=[ReservaShortItem.model_validate(item) for item in linked],
        gastos=[GastoItem.model_validate(item) for item in registered],
    )


@router.patch("/partidos/{partido_id}", response_model=PartidoResponse)
async def update_partido(
    partido_id: UUID,
    payload: PartidoUpdate,
    partidos: PartidoRepo,
    reservas: ReservaRepo,
    gastos: GastoRepo,
    _current_user: CurrentUser,
) -> PartidoResponse:
    """Partially update a partido (JWT required)."""
    existing = await partidos.get_by_id(partido_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Partido {partido_id} not found",
        )
    updated = existing.model_copy(
        update={
            **payload.model_dump(exclude_unset=True),
            "updated_at": datetime.now(UTC),
        },
    )
    saved = await partidos.save(updated)
    linked = await reservas.list_by_partido(saved.id)
    registered = await gastos.list_by_partido(saved.id)
    return PartidoResponse(
        **saved.model_dump(),
        reservas=[ReservaShortItem.model_validate(item) for item in linked],
        gastos=[GastoItem.model_validate(item) for item in registered],
    )


@router.delete(
    "/partidos/{partido_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_partido(
    partido_id: UUID,
    partidos: PartidoRepo,
    reservas: ReservaRepo,
    _current_user: CurrentUser,
) -> None:
    """Soft-delete a partido and unlink it from any reservas (JWT required)."""
    deleted = await partidos.soft_delete(partido_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Partido {partido_id} not found",
        )
    await reservas.unlink_partido(partido_id)

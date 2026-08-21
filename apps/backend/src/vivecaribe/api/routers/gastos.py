"""Gasto HTTP routes — partido-scoped expense CRUD.

A gasto only ever exists as at most one row per ``(partido_id,
categoria)``: the operator sets or clears a category's amount rather than
creating/deleting arbitrary rows. Every mutation returns the full
``PartidoResponse`` (mirroring ``vivecaribe.api.routers.partidos``) so the
frontend can replace its partido state wholesale, including the
recomputed reserva splits reflected in each linked reserva's ``costos``.

``categoria`` is a query parameter, not a path segment: several category
values (e.g. "Comida y/o Snacks") contain a literal ``/``, which breaks
path-segment routing even when percent-encoded — ASGI servers decode
``%2F`` before route matching, so a single ``{categoria}`` path parameter
can never match it. Query values have no such restriction.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from vivecaribe.api.deps import CurrentUser, GastoRepo, PartidoRepo, ReservaRepo
from vivecaribe.api.schemas.gastos import GastoItem, GastoUpsert
from vivecaribe.api.schemas.partidos import PartidoResponse
from vivecaribe.api.schemas.reservas import ReservaShortItem
from vivecaribe.domain.enums import GastoCategoria

router = APIRouter(tags=["gastos"])


@router.put("/partidos/{partido_id}/gastos", response_model=PartidoResponse)
async def upsert_gasto(
    partido_id: UUID,
    categoria: GastoCategoria,
    payload: GastoUpsert,
    gastos: GastoRepo,
    partidos: PartidoRepo,
    reservas: ReservaRepo,
    _current_user: CurrentUser,
) -> PartidoResponse:
    """Set (create or update) the amount for one gasto category (JWT required)."""
    partido = await partidos.get_by_id(partido_id)
    if partido is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Partido {partido_id} not found",
        )
    await gastos.upsert(partido_id, categoria, payload.monto)
    linked = await reservas.list_by_partido(partido.id)
    registered = await gastos.list_by_partido(partido.id)
    return PartidoResponse(
        **partido.model_dump(),
        reservas=[ReservaShortItem.model_validate(item) for item in linked],
        gastos=[GastoItem.model_validate(item) for item in registered],
    )


@router.delete("/partidos/{partido_id}/gastos", response_model=PartidoResponse)
async def delete_gasto(
    partido_id: UUID,
    categoria: GastoCategoria,
    gastos: GastoRepo,
    partidos: PartidoRepo,
    reservas: ReservaRepo,
    _current_user: CurrentUser,
) -> PartidoResponse:
    """Remove one gasto category's amount (JWT required)."""
    partido = await partidos.get_by_id(partido_id)
    if partido is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Partido {partido_id} not found",
        )
    await gastos.delete(partido_id, categoria)
    linked = await reservas.list_by_partido(partido.id)
    registered = await gastos.list_by_partido(partido.id)
    return PartidoResponse(
        **partido.model_dump(),
        reservas=[ReservaShortItem.model_validate(item) for item in linked],
        gastos=[GastoItem.model_validate(item) for item in registered],
    )

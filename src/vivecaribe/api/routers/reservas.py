"""Reserva HTTP routes — thin wrappers over the repository."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from vivecaribe.api.deps import CurrentUser, ReservaRepo
from vivecaribe.api.schemas.reservas import (
    ReservaCreate,
    ReservaListResponse,
    ReservaResponse,
    ReservaUpdate,
)
from vivecaribe.domain.reserva import Reserva

router = APIRouter(tags=["reservas"])


@router.post(
    "/reservas",
    response_model=ReservaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_reserva(
    payload: ReservaCreate,
    reservas: ReservaRepo,
    _current_user: CurrentUser,
) -> ReservaResponse:
    """Create a reservation (JWT required).

    Conflicts on the idempotency key
    ``(booking_provider, reserva_reference)``.
    """
    reserva = Reserva(**payload.model_dump())
    saved, created = await reservas.get_or_create(reserva)
    if not created:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Reserva already exists for "
                f"({payload.booking_provider.value}, "
                f"{payload.reserva_reference})"
            ),
        )
    return ReservaResponse.model_validate(saved)


@router.get("/reservas", response_model=ReservaListResponse)
async def list_reservas(
    reservas: ReservaRepo,
    _current_user: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ReservaListResponse:
    """Return a paginated list of reservations (JWT required)."""
    items, total = await reservas.list(skip=skip, limit=limit)
    return ReservaListResponse(
        total=total,
        items=[ReservaResponse.model_validate(item) for item in items],
    )


@router.get("/reservas/{reserva_id}", response_model=ReservaResponse)
async def get_reserva(
    reserva_id: UUID,
    reservas: ReservaRepo,
    _current_user: CurrentUser,
) -> ReservaResponse:
    """Return a single reservation by id (JWT required)."""
    reserva = await reservas.get_by_id(reserva_id)
    if reserva is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reserva {reserva_id} not found",
        )
    return ReservaResponse.model_validate(reserva)


@router.patch("/reservas/{reserva_id}", response_model=ReservaResponse)
async def update_reserva(
    reserva_id: UUID,
    payload: ReservaUpdate,
    reservas: ReservaRepo,
    _current_user: CurrentUser,
) -> ReservaResponse:
    """Partially update a reservation (JWT required)."""
    existing = await reservas.get_by_id(reserva_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reserva {reserva_id} not found",
        )
    updated = existing.model_copy(
        update={
            **payload.model_dump(exclude_unset=True),
            "updated_at": datetime.now(UTC),
        },
    )
    saved = await reservas.save(updated)
    return ReservaResponse.model_validate(saved)

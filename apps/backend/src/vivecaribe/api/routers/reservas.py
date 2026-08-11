"""Reserva HTTP routes — thin wrappers over the repository."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from vivecaribe.api.deps import CurrentUser, ReservaRepo
from vivecaribe.api.schemas.reservas import (
    ReservaCreate,
    ReservaListResponse,
    ReservaResponse,
    ReservaShortItem,
    ReservaUpdate,
)
from vivecaribe.domain.enums import BookingProvider, ReservaEstado
from vivecaribe.domain.reserva import Reserva, compute_paid_at

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
    data = payload.model_dump()
    reserva = Reserva(
        **data,
        paid_at=compute_paid_at(
            payload.booking_provider,
            payload.fecha_evento,
        ),
    )
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
    estado: Annotated[ReservaEstado | None, Query()] = None,
    booking_provider: Annotated[BookingProvider | None, Query()] = None,
    fecha_evento_from: Annotated[
        date | None,
        Query(description="Inclusive lower bound (America/Bogota calendar day)"),
    ] = None,
    fecha_evento_to: Annotated[
        date | None,
        Query(description="Inclusive upper bound (America/Bogota calendar day)"),
    ] = None,
) -> ReservaListResponse:
    """Return a filtered, paginated list of reservations (JWT required).

    Filters compose with AND. Omitted params mean no constraint. When either
    fecha bound is set, rows with null ``fecha_evento`` are excluded.
    """
    items, total = await reservas.list(
        skip=skip,
        limit=limit,
        estado=estado,
        booking_provider=booking_provider,
        fecha_evento_from=fecha_evento_from,
        fecha_evento_to=fecha_evento_to,
    )
    return ReservaListResponse(
        total=total,
        items=[ReservaShortItem.model_validate(item) for item in items],
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
    updated = updated.model_copy(
        update={
            "paid_at": compute_paid_at(
                updated.booking_provider,
                updated.fecha_evento,
            ),
        },
    )
    saved = await reservas.save(updated)
    return ReservaResponse.model_validate(saved)


@router.delete(
    "/reservas/{reserva_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_reserva(
    reserva_id: UUID,
    reservas: ReservaRepo,
    _current_user: CurrentUser,
) -> None:
    """Soft-delete a reservation (JWT required)."""
    deleted = await reservas.soft_delete(reserva_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reserva {reserva_id} not found",
        )

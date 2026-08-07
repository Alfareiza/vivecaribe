"""Reserva HTTP routes — thin wrappers over the repository."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from vivecaribe.api.deps import CurrentUser, ReservaRepo
from vivecaribe.api.schemas.reservas import ReservaCreate, ReservaResponse
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

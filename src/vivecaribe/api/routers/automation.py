"""Automation HTTP routes — thin wrappers over use cases."""

from __future__ import annotations

from fastapi import APIRouter

from vivecaribe.api.deps import CurrentUser, ProcessBookingEmailsDep
from vivecaribe.api.schemas.automation import GetBookingsRequest, GetBookingsResponse

router = APIRouter(prefix="/automation", tags=["automation"])


@router.post("/emails/get-bookings", response_model=GetBookingsResponse)
async def get_bookings(
    use_case: ProcessBookingEmailsDep,
    _user: CurrentUser,
    payload: GetBookingsRequest | None = None,
) -> GetBookingsResponse:
    """Fetch booking emails, extract reservas, optionally notify WhatsApp."""
    body = payload or GetBookingsRequest()
    result = await use_case.start(
        booking_provider=body.booking_provider,
        notify=body.notify,
    )
    return GetBookingsResponse(
        fetched=result.fetched,
        created=result.created,
        existing=result.existing,
        notified=result.notified,
    )

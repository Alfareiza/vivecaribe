"""Automation HTTP routes — thin wrappers over use cases."""

from __future__ import annotations

from fastapi import APIRouter

from vivecaribe.api.deps import AutomationAuth, ProcessBookingEmailsDep
from vivecaribe.api.schemas.automation import GetBookingsRequest, GetBookingsResponse
from vivecaribe.application.automation.use_cases import ProcessBookingEmailsUseCase

router = APIRouter(prefix="/automation", tags=["automation"])


def _response_from_use_case(
    result: ProcessBookingEmailsUseCase,
) -> GetBookingsResponse:
    """Map pipeline counters to the HTTP response schema."""
    return GetBookingsResponse(
        fetched=result.fetched,
        created=result.created,
        existing=result.existing,
        notified=result.notified,
    )


@router.get("/emails/get-bookings", response_model=GetBookingsResponse)
async def get_bookings_get(
    use_case: ProcessBookingEmailsDep,
    _auth: AutomationAuth,
) -> GetBookingsResponse:
    """Run the pipeline with defaults (all providers, ``notify=False``).

    Intended for Vercel Cron (GET + Bearer ``CRON_SECRET``). Also accepts JWT.
    No request body.
    """
    result = await use_case.start(booking_provider=None, notify=False)
    return _response_from_use_case(result)


@router.post("/emails/get-bookings", response_model=GetBookingsResponse)
async def get_bookings_post(
    use_case: ProcessBookingEmailsDep,
    _auth: AutomationAuth,
    payload: GetBookingsRequest | None = None,
) -> GetBookingsResponse:
    """Fetch booking emails, extract reservas, optionally notify WhatsApp.

    Auth: Bearer JWT (operator) or Bearer ``CRON_SECRET``. Optional JSON body
    may filter ``booking_provider`` and set ``notify``.
    """
    body = payload or GetBookingsRequest()
    result = await use_case.start(
        booking_provider=body.booking_provider,
        notify=body.notify,
    )
    return _response_from_use_case(result)

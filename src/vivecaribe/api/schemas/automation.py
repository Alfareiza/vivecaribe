"""Request/response schemas for automation endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

from vivecaribe.domain.enums import BookingProvider


class GetBookingsRequest(BaseModel):
    """Optional filters for ``POST /automation/emails/get-bookings``."""

    booking_provider: BookingProvider | None = None
    notify: bool = False


class GetBookingsResponse(BaseModel):
    """Aggregate counters from one pipeline run."""

    fetched: int = Field(ge=0)
    created: int = Field(ge=0)
    existing: int = Field(ge=0)
    notified: int = Field(ge=0)

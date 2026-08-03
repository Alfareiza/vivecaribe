"""API tests for POST /automation/emails/get-bookings."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from vivecaribe.api import deps
from vivecaribe.domain.enums import BookingProvider
from vivecaribe.domain.user import User
from vivecaribe.main import create_app


def _fake_user() -> User:
    return User(
        id=uuid4(),
        email="ops@vivecaribe.com",
        password_hash="not-used",
        is_active=True,
    )


def _mock_use_case() -> MagicMock:
    use_case = MagicMock()
    use_case.fetched = 3
    use_case.created = 2
    use_case.existing = 1
    use_case.notified = 0
    use_case.start = AsyncMock(return_value=use_case)
    return use_case


@pytest.mark.asyncio
async def test_get_bookings_requires_jwt() -> None:
    """Missing Bearer token returns 401."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/automation/emails/get-bookings")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_bookings_happy_path_maps_counters() -> None:
    """Authenticated call maps use-case counters into the response body."""
    use_case = _mock_use_case()
    app = create_app()
    app.dependency_overrides[deps.get_current_user] = _fake_user
    app.dependency_overrides[deps.get_process_booking_emails_use_case] = (
        lambda: use_case
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/automation/emails/get-bookings",
            json={"booking_provider": "getyourguide", "notify": False},
            headers={"Authorization": "Bearer unused"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "fetched": 3,
        "created": 2,
        "existing": 1,
        "notified": 0,
    }
    use_case.start.assert_awaited_once_with(
        booking_provider=BookingProvider.GETYOURGUIDE,
        notify=False,
    )

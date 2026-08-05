"""API tests for GET/POST /automation/emails/get-bookings."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from vivecaribe.api import deps
from vivecaribe.domain.enums import BookingProvider
from vivecaribe.main import create_app
from tests.conftest import auth_headers

_CRON_HEADERS = {
    "Authorization": "Bearer test-cron-secret-not-for-production",
}


def _mock_use_case() -> MagicMock:
    use_case = MagicMock()
    use_case.fetched = 3
    use_case.created = 2
    use_case.existing = 1
    use_case.notified = 0
    use_case.start = AsyncMock(return_value=use_case)
    return use_case


@pytest.fixture
async def automation_client(
    db_engine: AsyncEngine,
) -> AsyncIterator[tuple[AsyncClient, MagicMock]]:
    """App client with test DB and a mocked booking-email use case."""
    use_case = _mock_use_case()
    factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app = create_app()
    app.dependency_overrides[deps.get_db_session] = override_get_db_session
    app.dependency_overrides[deps.get_process_booking_emails_use_case] = (
        lambda: use_case
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, use_case

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_bookings_post_requires_auth() -> None:
    """Missing Bearer token on POST returns 401."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/automation/emails/get-bookings")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_bookings_get_requires_auth() -> None:
    """Missing Bearer token on GET returns 401."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/automation/emails/get-bookings")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_bookings_invalid_token_returns_401() -> None:
    """A garbled Bearer token that is not CRON_SECRET returns 401."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/automation/emails/get-bookings",
            headers={"Authorization": "Bearer not-a-real-token"},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_bookings_get_accepts_cron_secret(
    automation_client: tuple[AsyncClient, MagicMock],
) -> None:
    """GET with CRON_SECRET runs the pipeline with defaults (Vercel Cron path)."""
    client, use_case = automation_client
    response = await client.get(
        "/automation/emails/get-bookings",
        headers=_CRON_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {
        "fetched": 3,
        "created": 2,
        "existing": 1,
        "notified": 0,
    }
    use_case.start.assert_awaited_once_with(
        booking_provider=None,
        notify=False,
    )


@pytest.mark.asyncio
async def test_get_bookings_post_accepts_cron_secret(
    automation_client: tuple[AsyncClient, MagicMock],
) -> None:
    """POST with CRON_SECRET also authenticates without a user JWT."""
    client, use_case = automation_client
    response = await client.post(
        "/automation/emails/get-bookings",
        json={"notify": False},
        headers=_CRON_HEADERS,
    )

    assert response.status_code == 200
    use_case.start.assert_awaited_once_with(
        booking_provider=None,
        notify=False,
    )


@pytest.mark.asyncio
async def test_get_bookings_post_jwt_maps_counters(
    automation_client: tuple[AsyncClient, MagicMock],
) -> None:
    """POST with a real JWT maps use-case counters and body filters."""
    client, use_case = automation_client
    headers = await auth_headers(client)

    response = await client.post(
        "/automation/emails/get-bookings",
        json={"booking_provider": "getyourguide", "notify": False},
        headers=headers,
    )

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

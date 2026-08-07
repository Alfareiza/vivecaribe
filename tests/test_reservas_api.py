"""API tests for reserva CRUD endpoints."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


def _reserva_payload(**overrides: Any) -> dict[str, Any]:
    """Build a valid ``POST /reservas`` body with optional overrides."""
    payload: dict[str, Any] = {
        "source": "gmail",
        "booking_provider": "getyourguide",
        "reserva_reference": "GYG-1001",
        "sender": "bookings@getyourguide.com",
        "estado": "en_progreso",
        "subject": "New booking",
        "fecha_email_recibido": "2026-07-01T12:00:00Z",
        "nombre_experiencia": "City Tour",
        "ciudad_experiencia": "Cartagena",
        "fecha_evento": "2026-08-15T09:00:00Z",
        "participants": 2,
        "customer_name": "Ada Lovelace",
        "phone": "+573001112233",
        "pais_del_visitante": "CO",
        "moneda": "USD",
        "price": "120.50",
        "income": "84.35",
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_create_reserva_returns_201(auth_client: AsyncClient) -> None:
    """Authenticated create returns 201 with the persisted reserva."""
    headers = await auth_headers(auth_client)
    response = await auth_client.post(
        "/reservas",
        json=_reserva_payload(),
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["reserva_reference"] == "GYG-1001"
    assert body["booking_provider"] == "getyourguide"
    assert body["customer_name"] == "Ada Lovelace"
    assert body["id"]
    assert "created_at" in body


@pytest.mark.asyncio
async def test_create_reserva_duplicate_returns_409(
    auth_client: AsyncClient,
) -> None:
    """Duplicate ``(booking_provider, reserva_reference)`` returns 409."""
    headers = await auth_headers(auth_client)
    payload = _reserva_payload(reserva_reference="GYG-DUP")
    first = await auth_client.post("/reservas", json=payload, headers=headers)
    second = await auth_client.post("/reservas", json=payload, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 409
    assert "already exists" in second.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_reserva_unauthenticated_returns_401(
    auth_client: AsyncClient,
) -> None:
    """Missing Bearer token returns 401."""
    response = await auth_client.post("/reservas", json=_reserva_payload())
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_reserva_invalid_payload_returns_422(
    auth_client: AsyncClient,
) -> None:
    """Invalid enum / missing fields are rejected by the schema."""
    headers = await auth_headers(auth_client)
    response = await auth_client.post(
        "/reservas",
        json=_reserva_payload(estado="not-a-valid-estado"),
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_reserva_returns_200(auth_client: AsyncClient) -> None:
    """Authenticated get-by-id returns the created reserva."""
    headers = await auth_headers(auth_client)
    created = await auth_client.post(
        "/reservas",
        json=_reserva_payload(reserva_reference="GYG-GET-1"),
        headers=headers,
    )
    assert created.status_code == 201
    reserva_id = created.json()["id"]

    response = await auth_client.get(f"/reservas/{reserva_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == reserva_id
    assert response.json()["reserva_reference"] == "GYG-GET-1"


@pytest.mark.asyncio
async def test_get_reserva_missing_returns_404(auth_client: AsyncClient) -> None:
    """Unknown UUID returns 404."""
    headers = await auth_headers(auth_client)
    response = await auth_client.get(f"/reservas/{uuid4()}", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_reserva_unauthenticated_returns_401(
    auth_client: AsyncClient,
) -> None:
    """Missing Bearer token returns 401."""
    response = await auth_client.get(f"/reservas/{uuid4()}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_reservas_paginates(auth_client: AsyncClient) -> None:
    """List returns total and a skip/limit page slice."""
    headers = await auth_headers(auth_client)
    for i in range(3):
        created = await auth_client.post(
            "/reservas",
            json=_reserva_payload(reserva_reference=f"GYG-LIST-{i}"),
            headers=headers,
        )
        assert created.status_code == 201

    page = await auth_client.get(
        "/reservas",
        params={"skip": 0, "limit": 2},
        headers=headers,
    )
    assert page.status_code == 200
    body = page.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2

    rest = await auth_client.get(
        "/reservas",
        params={"skip": 2, "limit": 2},
        headers=headers,
    )
    assert rest.status_code == 200
    assert rest.json()["total"] == 3
    assert len(rest.json()["items"]) == 1


@pytest.mark.asyncio
async def test_list_reservas_empty(auth_client: AsyncClient) -> None:
    """Empty database returns total 0 and empty items."""
    headers = await auth_headers(auth_client)
    response = await auth_client.get("/reservas", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"total": 0, "items": []}


@pytest.mark.asyncio
async def test_list_reservas_unauthenticated_returns_401(
    auth_client: AsyncClient,
) -> None:
    """Missing Bearer token returns 401."""
    response = await auth_client.get("/reservas")
    assert response.status_code == 401

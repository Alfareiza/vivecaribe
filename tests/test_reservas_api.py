"""API tests for reserva CRUD endpoints."""

from __future__ import annotations

from typing import Any

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

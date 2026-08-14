"""API tests for partido CRUD endpoints and their link to reservas."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


def _partido_payload(**overrides: Any) -> dict[str, Any]:
    """Build a valid ``POST /partidos`` body with optional overrides."""
    payload: dict[str, Any] = {
        "equipo_local": "Junior",
        "equipo_visitante": "Millonarios",
        "nombre_campeonato": "Colombian League",
        "estadio": "Metropolitano",
        "fecha": "2026-09-01T20:00:00Z",
        "ciudad": "Barranquilla",
    }
    payload.update(overrides)
    return payload


def _reserva_payload(**overrides: Any) -> dict[str, Any]:
    """Build a valid ``POST /reservas`` body with optional overrides."""
    payload: dict[str, Any] = {
        "source": "gmail",
        "booking_provider": "getyourguide",
        "reserva_reference": f"GYG-{uuid4()}",
        "sender": "bookings@getyourguide.com",
        "estado": "en_progreso",
        "subject": "New booking",
        "fecha_email_recibido": "2026-07-01T12:00:00Z",
        "nombre_experiencia": "football tour",
        "ciudad_experiencia": "Barranquilla",
        "fecha_evento": "2026-09-01T20:00:00Z",
        "participants": 2,
        "customer_name": "Ada Lovelace",
        "price": "120.50",
        "income": "84.35",
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_create_partido_returns_201(auth_client: AsyncClient) -> None:
    """Authenticated create returns 201 with the persisted partido."""
    headers = await auth_headers(auth_client)
    response = await auth_client.post(
        "/partidos",
        json=_partido_payload(),
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["equipo_local"] == "Junior"
    assert body["equipo_visitante"] == "Millonarios"
    assert body["nombre_campeonato"] == "Colombian League"
    assert body["estadio"] == "Metropolitano"
    assert body["ciudad"] == "Barranquilla"
    assert body["reservas"] == []
    assert body["id"]
    assert "created_at" in body
    assert "deleted_at" not in body


@pytest.mark.asyncio
async def test_create_partido_invalid_campeonato_returns_422(
    auth_client: AsyncClient,
) -> None:
    """An unlisted ``nombre_campeonato`` value is rejected."""
    headers = await auth_headers(auth_client)
    response = await auth_client.post(
        "/partidos",
        json=_partido_payload(nombre_campeonato="Not A Real Championship"),
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_partido_invalid_estadio_returns_422(
    auth_client: AsyncClient,
) -> None:
    """An unlisted ``estadio`` value is rejected."""
    headers = await auth_headers(auth_client)
    response = await auth_client.post(
        "/partidos",
        json=_partido_payload(estadio="Not A Real Stadium"),
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_partido_invalid_ciudad_returns_422(
    auth_client: AsyncClient,
) -> None:
    """An unlisted ``ciudad`` value is rejected."""
    headers = await auth_headers(auth_client)
    response = await auth_client.post(
        "/partidos",
        json=_partido_payload(ciudad="Bogotá"),
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_partido_unauthenticated_returns_401(
    auth_client: AsyncClient,
) -> None:
    """Missing bearer token yields 401."""
    response = await auth_client.post("/partidos", json=_partido_payload())
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_partido_returns_200(auth_client: AsyncClient) -> None:
    """Detail fetch returns the persisted partido."""
    headers = await auth_headers(auth_client)
    created = await auth_client.post(
        "/partidos",
        json=_partido_payload(),
        headers=headers,
    )
    partido_id = created.json()["id"]

    response = await auth_client.get(f"/partidos/{partido_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == partido_id


@pytest.mark.asyncio
async def test_get_partido_missing_returns_404(auth_client: AsyncClient) -> None:
    """Unknown id yields 404."""
    headers = await auth_headers(auth_client)
    response = await auth_client.get(f"/partidos/{uuid4()}", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_partidos_orders_by_fecha_ascending(
    auth_client: AsyncClient,
) -> None:
    """List defaults to soonest-first ordering."""
    headers = await auth_headers(auth_client)
    later = await auth_client.post(
        "/partidos",
        json=_partido_payload(fecha="2026-10-01T20:00:00Z"),
        headers=headers,
    )
    sooner = await auth_client.post(
        "/partidos",
        json=_partido_payload(fecha="2026-09-01T20:00:00Z"),
        headers=headers,
    )

    response = await auth_client.get("/partidos", headers=headers)
    assert response.status_code == 200
    body = response.json()
    ids = [item["id"] for item in body["items"]]
    assert ids.index(sooner.json()["id"]) < ids.index(later.json()["id"])


@pytest.mark.asyncio
async def test_list_partidos_filters_by_ciudad(auth_client: AsyncClient) -> None:
    """``ciudad`` filter narrows the list case-insensitively."""
    headers = await auth_headers(auth_client)
    await auth_client.post(
        "/partidos",
        json=_partido_payload(ciudad="Barranquilla"),
        headers=headers,
    )
    await auth_client.post(
        "/partidos",
        json=_partido_payload(ciudad="Cartagena", estadio="Jaime Morón"),
        headers=headers,
    )

    response = await auth_client.get(
        "/partidos",
        params={"ciudad": "cartagena"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["ciudad"] == "Cartagena"


@pytest.mark.asyncio
async def test_patch_partido_partial_update(auth_client: AsyncClient) -> None:
    """PATCH updates only the provided fields."""
    headers = await auth_headers(auth_client)
    created = await auth_client.post(
        "/partidos",
        json=_partido_payload(),
        headers=headers,
    )
    partido_id = created.json()["id"]

    response = await auth_client.patch(
        f"/partidos/{partido_id}",
        json={"estadio": "Jaime Morón", "equipo_visitante": "América"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["estadio"] == "Jaime Morón"
    assert body["equipo_visitante"] == "América"
    assert body["equipo_local"] == "Junior"


@pytest.mark.asyncio
async def test_patch_partido_missing_returns_404(auth_client: AsyncClient) -> None:
    """PATCH on an unknown id yields 404."""
    headers = await auth_headers(auth_client)
    response = await auth_client.patch(
        f"/partidos/{uuid4()}",
        json={"ciudad": "Cartagena"},
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_partido_embeds_linked_reservas(auth_client: AsyncClient) -> None:
    """Linking a reserva to a partido surfaces it on the partido detail."""
    headers = await auth_headers(auth_client)
    partido = (
        await auth_client.post("/partidos", json=_partido_payload(), headers=headers)
    ).json()

    reserva = (
        await auth_client.post(
            "/reservas",
            json=_reserva_payload(partido_id=partido["id"]),
            headers=headers,
        )
    ).json()
    assert reserva["partido_id"] == partido["id"]

    detail = await auth_client.get(f"/partidos/{partido['id']}", headers=headers)
    linked_ids = [item["id"] for item in detail.json()["reservas"]]
    assert linked_ids == [reserva["id"]]


@pytest.mark.asyncio
async def test_delete_partido_soft_deletes_and_unlinks_reservas(
    auth_client: AsyncClient,
) -> None:
    """Deleting a partido soft-deletes it and clears ``partido_id`` on reservas."""
    headers = await auth_headers(auth_client)
    partido = (
        await auth_client.post("/partidos", json=_partido_payload(), headers=headers)
    ).json()
    reserva = (
        await auth_client.post(
            "/reservas",
            json=_reserva_payload(partido_id=partido["id"]),
            headers=headers,
        )
    ).json()

    response = await auth_client.delete(f"/partidos/{partido['id']}", headers=headers)
    assert response.status_code == 204

    missing = await auth_client.get(f"/partidos/{partido['id']}", headers=headers)
    assert missing.status_code == 404

    reserva_after = await auth_client.get(
        f"/reservas/{reserva['id']}",
        headers=headers,
    )
    assert reserva_after.json()["partido_id"] is None


@pytest.mark.asyncio
async def test_delete_partido_missing_returns_404(auth_client: AsyncClient) -> None:
    """DELETE on an unknown id yields 404."""
    headers = await auth_headers(auth_client)
    response = await auth_client.delete(f"/partidos/{uuid4()}", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_partido_unauthenticated_returns_401(
    auth_client: AsyncClient,
) -> None:
    """Missing bearer token yields 401."""
    response = await auth_client.delete(f"/partidos/{uuid4()}")
    assert response.status_code == 401

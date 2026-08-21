"""API tests for gasto endpoints and reserva-split recomputation."""

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
        "source": "manual",
        "booking_provider": "propio",
        "reserva_reference": f"GT-{uuid4()}",
        "estado": "confirmada",
        "nombre_experiencia": "Watch Junior de Barranquilla Match",
        "ciudad_experiencia": "Barranquilla",
        "fecha_evento": "2026-09-01T20:00:00Z",
        "participants": 1,
        "customer_name": "Ada Lovelace",
        "moneda": "COP",
        "price": "100000.00",
        "income": "100000.00",
    }
    payload.update(overrides)
    return payload


async def _create_partido(client: AsyncClient, headers: dict[str, str]) -> str:
    response = await client.post("/partidos", json=_partido_payload(), headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


async def _create_reserva(
    client: AsyncClient,
    headers: dict[str, str],
    **overrides: Any,
) -> dict[str, Any]:
    response = await client.post(
        "/reservas",
        json=_reserva_payload(**overrides),
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_upsert_gasto_creates_then_updates_same_category(
    auth_client: AsyncClient,
) -> None:
    """PUT is create-or-update — at most one row per (partido, categoria)."""
    headers = await auth_headers(auth_client)
    partido_id = await _create_partido(auth_client, headers)

    created = await auth_client.put(
        f"/partidos/{partido_id}/gastos",
        params={"categoria": "Boletas"},
        json={"monto": "50000.00"},
        headers=headers,
    )
    assert created.status_code == 200
    body = created.json()
    assert body["gastos"] == [{"categoria": "Boletas", "monto": "50000.00"}]
    assert body["gastos_total"] == "50000.00"

    updated = await auth_client.put(
        f"/partidos/{partido_id}/gastos",
        params={"categoria": "Boletas"},
        json={"monto": "70000.00"},
        headers=headers,
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["gastos"] == [{"categoria": "Boletas", "monto": "70000.00"}]
    assert body["gastos_total"] == "70000.00"


@pytest.mark.asyncio
async def test_upsert_gasto_slash_categoria_via_query_param(
    auth_client: AsyncClient,
) -> None:
    """"Comida y/o Snacks" contains a literal "/" — must route via query param."""
    headers = await auth_headers(auth_client)
    partido_id = await _create_partido(auth_client, headers)

    response = await auth_client.put(
        f"/partidos/{partido_id}/gastos",
        params={"categoria": "Comida y/o Snacks"},
        json={"monto": "15000.00"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["gastos"] == [
        {"categoria": "Comida y/o Snacks", "monto": "15000.00"},
    ]


@pytest.mark.asyncio
async def test_upsert_gasto_unknown_partido_returns_404(
    auth_client: AsyncClient,
) -> None:
    """A gasto write against a missing partido 404s instead of creating an orphan row."""
    headers = await auth_headers(auth_client)
    response = await auth_client.put(
        f"/partidos/{uuid4()}/gastos",
        params={"categoria": "Boletas"},
        json={"monto": "10000.00"},
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_gasto_removes_category_and_recomputes(
    auth_client: AsyncClient,
) -> None:
    """DELETE clears one category and its split, leaving the rest untouched."""
    headers = await auth_headers(auth_client)
    partido_id = await _create_partido(auth_client, headers)
    reserva = await _create_reserva(auth_client, headers, partido_id=partido_id)

    await auth_client.put(
        f"/partidos/{partido_id}/gastos",
        params={"categoria": "Transporte"},
        json={"monto": "80000.00"},
        headers=headers,
    )
    await auth_client.put(
        f"/partidos/{partido_id}/gastos",
        params={"categoria": "Boletas"},
        json={"monto": "40000.00"},
        headers=headers,
    )

    deleted = await auth_client.delete(
        f"/partidos/{partido_id}/gastos",
        params={"categoria": "Boletas"},
        headers=headers,
    )
    assert deleted.status_code == 200
    body = deleted.json()
    assert body["gastos"] == [{"categoria": "Transporte", "monto": "80000.00"}]
    assert body["gastos_total"] == "80000.00"

    reserva_body = (
        await auth_client.get(f"/reservas/{reserva['id']}", headers=headers)
    ).json()
    assert reserva_body["costos"] == "80000.00"


@pytest.mark.asyncio
async def test_delete_gasto_never_registered_is_a_noop(
    auth_client: AsyncClient,
) -> None:
    """Deleting a category with no gasto row still succeeds, changing nothing."""
    headers = await auth_headers(auth_client)
    partido_id = await _create_partido(auth_client, headers)

    response = await auth_client.delete(
        f"/partidos/{partido_id}/gastos",
        params={"categoria": "Otros"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["gastos"] == []


@pytest.mark.asyncio
async def test_split_proportional_to_participants(
    auth_client: AsyncClient,
) -> None:
    """A gasto splits across linked reservas proportionally to participants."""
    headers = await auth_headers(auth_client)
    partido_id = await _create_partido(auth_client, headers)
    alice = await _create_reserva(
        auth_client,
        headers,
        customer_name="Alice",
        participants=3,
        partido_id=partido_id,
    )
    bob = await _create_reserva(
        auth_client,
        headers,
        customer_name="Bob",
        participants=1,
        partido_id=partido_id,
    )

    await auth_client.put(
        f"/partidos/{partido_id}/gastos",
        params={"categoria": "Transporte"},
        json={"monto": "80000.00"},
        headers=headers,
    )
    await auth_client.put(
        f"/partidos/{partido_id}/gastos",
        params={"categoria": "Boletas"},
        json={"monto": "40000.00"},
        headers=headers,
    )

    alice_body = (
        await auth_client.get(f"/reservas/{alice['id']}", headers=headers)
    ).json()
    bob_body = (
        await auth_client.get(f"/reservas/{bob['id']}", headers=headers)
    ).json()

    # 120000 total, split 3:1 -> Alice 90000 (3/4), Bob 30000 (1/4).
    assert alice_body["costos"] == "90000.00"
    assert alice_body["gastos_total"] == "90000.00"
    assert {g["categoria"]: g["monto"] for g in alice_body["gastos"]} == {
        "Transporte": "60000.00",
        "Boletas": "30000.00",
    }
    assert bob_body["costos"] == "30000.00"
    assert {g["categoria"]: g["monto"] for g in bob_body["gastos"]} == {
        "Transporte": "20000.00",
        "Boletas": "10000.00",
    }


@pytest.mark.asyncio
async def test_split_excludes_cancelled_reserva(auth_client: AsyncClient) -> None:
    """Cancelling a reserva drops it from the split and clears its ``costos``."""
    headers = await auth_headers(auth_client)
    partido_id = await _create_partido(auth_client, headers)
    alice = await _create_reserva(
        auth_client,
        headers,
        customer_name="Alice",
        participants=3,
        partido_id=partido_id,
    )
    bob = await _create_reserva(
        auth_client,
        headers,
        customer_name="Bob",
        participants=1,
        partido_id=partido_id,
    )
    await auth_client.put(
        f"/partidos/{partido_id}/gastos",
        params={"categoria": "Transporte"},
        json={"monto": "80000.00"},
        headers=headers,
    )

    cancel = await auth_client.post(
        f"/reservas/{bob['id']}/cancelar",
        json={"motivo_cancelacion": "Cliente no llegó al punto de encuentro"},
        headers=headers,
    )
    assert cancel.status_code == 200
    assert cancel.json()["costos"] is None

    alice_body = (
        await auth_client.get(f"/reservas/{alice['id']}", headers=headers)
    ).json()
    bob_body = (
        await auth_client.get(f"/reservas/{bob['id']}", headers=headers)
    ).json()

    # Bob is cancelled and no longer part of the split, so Alice absorbs
    # the full 80000 despite the partido having 3+1 participants on paper.
    assert alice_body["costos"] == "80000.00"
    assert bob_body["costos"] is None


@pytest.mark.asyncio
async def test_split_recomputes_when_reserva_joins_partido(
    auth_client: AsyncClient,
) -> None:
    """Linking a new reserva to a partido with existing gastos redistributes shares."""
    headers = await auth_headers(auth_client)
    partido_id = await _create_partido(auth_client, headers)
    alice = await _create_reserva(
        auth_client,
        headers,
        customer_name="Alice",
        participants=3,
        partido_id=partido_id,
    )
    await auth_client.put(
        f"/partidos/{partido_id}/gastos",
        params={"categoria": "Transporte"},
        json={"monto": "80000.00"},
        headers=headers,
    )
    alice_body = (
        await auth_client.get(f"/reservas/{alice['id']}", headers=headers)
    ).json()
    assert alice_body["costos"] == "80000.00"

    carol = await _create_reserva(
        auth_client,
        headers,
        customer_name="Carol",
        participants=1,
    )
    linked = await auth_client.patch(
        f"/reservas/{carol['id']}",
        json={"partido_id": partido_id},
        headers=headers,
    )
    assert linked.status_code == 200

    alice_after = (
        await auth_client.get(f"/reservas/{alice['id']}", headers=headers)
    ).json()
    carol_after = linked.json()
    # 80000 split 3:1 -> Alice 60000, Carol 20000.
    assert alice_after["costos"] == "60000.00"
    assert carol_after["costos"] == "20000.00"


@pytest.mark.asyncio
async def test_costos_resets_to_null_when_reserva_unlinked(
    auth_client: AsyncClient,
) -> None:
    """Unlinking a reserva from its partido clears its derived costos."""
    headers = await auth_headers(auth_client)
    partido_id = await _create_partido(auth_client, headers)
    reserva = await _create_reserva(auth_client, headers, partido_id=partido_id)
    await auth_client.put(
        f"/partidos/{partido_id}/gastos",
        params={"categoria": "Transporte"},
        json={"monto": "50000.00"},
        headers=headers,
    )
    linked_body = (
        await auth_client.get(f"/reservas/{reserva['id']}", headers=headers)
    ).json()
    assert linked_body["costos"] == "50000.00"

    unlinked = await auth_client.patch(
        f"/reservas/{reserva['id']}",
        json={"partido_id": None},
        headers=headers,
    )
    assert unlinked.status_code == 200
    body = unlinked.json()
    assert body["partido_id"] is None
    assert body["costos"] is None
    assert body["gastos"] == []


@pytest.mark.asyncio
async def test_costos_null_until_first_gasto_registered(
    auth_client: AsyncClient,
) -> None:
    """A reserva linked to a partido with zero gastos has no costos yet (not zero)."""
    headers = await auth_headers(auth_client)
    partido_id = await _create_partido(auth_client, headers)
    reserva = await _create_reserva(auth_client, headers, partido_id=partido_id)

    body = (
        await auth_client.get(f"/reservas/{reserva['id']}", headers=headers)
    ).json()
    assert body["costos"] is None
    assert body["gastos"] == []
    assert body["gastos_total"] == "0"

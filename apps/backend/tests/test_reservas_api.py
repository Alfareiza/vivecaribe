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
    body = response.json()
    assert body["id"] == reserva_id
    assert body["reserva_reference"] == "GYG-GET-1"
    assert "es_hoy" in body
    assert isinstance(body["es_hoy"], bool)
    assert "deleted_at" not in body


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


_LIST_ITEM_KEYS = {
    "id",
    "booking_provider",
    "ciudad_experiencia",
    "nombre_experiencia",
    "participants",
    "pais_del_visitante",
    "phone",
    "fecha_evento",
    "customer_name",
    "moneda",
    "price",
    "income",
    "es_hoy",
}


@pytest.mark.asyncio
async def test_list_reservas_paginates(auth_client: AsyncClient) -> None:
    """List returns total and a skip/limit page slice of slim items."""
    headers = await auth_headers(auth_client)
    for i in range(3):
        created = await auth_client.post(
            "/reservas",
            json=_reserva_payload(
                reserva_reference=f"GYG-LIST-{i}",
                fecha_evento=f"2026-08-{15 + i:02d}T09:00:00Z",
            ),
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
    assert set(body["items"][0].keys()) == _LIST_ITEM_KEYS
    # Newest fecha_evento first
    assert body["items"][0]["fecha_evento"].startswith("2026-08-17")

    rest = await auth_client.get(
        "/reservas",
        params={"skip": 2, "limit": 2},
        headers=headers,
    )
    assert rest.status_code == 200
    assert rest.json()["total"] == 3
    assert len(rest.json()["items"]) == 1


@pytest.mark.asyncio
async def test_list_reservas_filters_compose(auth_client: AsyncClient) -> None:
    """estado, booking_provider, and fecha bounds AND together."""
    headers = await auth_headers(auth_client)
    fixtures = [
        _reserva_payload(
            reserva_reference="F-1",
            booking_provider="getyourguide",
            estado="confirmada",
            fecha_evento="2026-08-10T14:00:00Z",
        ),
        _reserva_payload(
            reserva_reference="F-2",
            booking_provider="viator",
            estado="confirmada",
            fecha_evento="2026-08-12T14:00:00Z",
        ),
        _reserva_payload(
            reserva_reference="F-3",
            booking_provider="getyourguide",
            estado="en_progreso",
            fecha_evento="2026-08-12T14:00:00Z",
        ),
        _reserva_payload(
            reserva_reference="F-4",
            booking_provider="getyourguide",
            estado="confirmada",
            fecha_evento="2026-08-20T14:00:00Z",
        ),
        _reserva_payload(
            reserva_reference="F-NULL",
            booking_provider="getyourguide",
            estado="confirmada",
            fecha_evento=None,
        ),
        _reserva_payload(
            reserva_reference="F-MATCH",
            booking_provider="getyourguide",
            estado="confirmada",
            fecha_evento="2026-08-12T14:00:00Z",
        ),
    ]
    for payload in fixtures:
        created = await auth_client.post(
            "/reservas",
            json=payload,
            headers=headers,
        )
        assert created.status_code == 201

    filtered = await auth_client.get(
        "/reservas",
        params={
            "estado": "confirmada",
            "booking_provider": "getyourguide",
            "fecha_evento_from": "2026-08-11",
            "fecha_evento_to": "2026-08-15",
        },
        headers=headers,
    )
    assert filtered.status_code == 200
    body = filtered.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["customer_name"] == "Ada Lovelace"
    assert "estado" not in body["items"][0]


@pytest.mark.asyncio
async def test_list_reservas_date_range_excludes_null_fecha(
    auth_client: AsyncClient,
) -> None:
    """Null fecha_evento rows drop out when any fecha bound is set."""
    headers = await auth_headers(auth_client)
    with_date = await auth_client.post(
        "/reservas",
        json=_reserva_payload(
            reserva_reference="DATED",
            fecha_evento="2026-09-01T15:00:00Z",
        ),
        headers=headers,
    )
    null_date = await auth_client.post(
        "/reservas",
        json=_reserva_payload(
            reserva_reference="NULL-FECHA",
            fecha_evento=None,
        ),
        headers=headers,
    )
    assert with_date.status_code == 201
    assert null_date.status_code == 201

    response = await auth_client.get(
        "/reservas",
        params={"fecha_evento_from": "2026-09-01", "fecha_evento_to": "2026-09-01"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["nombre_experiencia"] == "City Tour"


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


@pytest.mark.asyncio
async def test_patch_reserva_partial_update(auth_client: AsyncClient) -> None:
    """PATCH updates only the provided fields."""
    headers = await auth_headers(auth_client)
    created = await auth_client.post(
        "/reservas",
        json=_reserva_payload(reserva_reference="GYG-PATCH-1"),
        headers=headers,
    )
    assert created.status_code == 201
    reserva_id = created.json()["id"]

    response = await auth_client.patch(
        f"/reservas/{reserva_id}",
        json={"estado": "confirmada", "customer_name": "Grace Hopper"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["estado"] == "confirmada"
    assert body["customer_name"] == "Grace Hopper"
    assert body["reserva_reference"] == "GYG-PATCH-1"
    assert body["participants"] == 2


@pytest.mark.asyncio
async def test_patch_reserva_missing_returns_404(auth_client: AsyncClient) -> None:
    """Unknown UUID returns 404."""
    headers = await auth_headers(auth_client)
    response = await auth_client.patch(
        f"/reservas/{uuid4()}",
        json={"estado": "confirmada"},
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_patch_reserva_invalid_estado_returns_422(
    auth_client: AsyncClient,
) -> None:
    """Invalid enum values are rejected by the schema."""
    headers = await auth_headers(auth_client)
    created = await auth_client.post(
        "/reservas",
        json=_reserva_payload(reserva_reference="GYG-PATCH-422"),
        headers=headers,
    )
    assert created.status_code == 201

    response = await auth_client.patch(
        f"/reservas/{created.json()['id']}",
        json={"estado": "not-valid"},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_patch_reserva_unauthenticated_returns_401(
    auth_client: AsyncClient,
) -> None:
    """Missing Bearer token returns 401."""
    response = await auth_client.patch(
        f"/reservas/{uuid4()}",
        json={"estado": "confirmada"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_reserva_soft_deletes(auth_client: AsyncClient) -> None:
    """DELETE soft-deletes; subsequent GET returns 404."""
    headers = await auth_headers(auth_client)
    created = await auth_client.post(
        "/reservas",
        json=_reserva_payload(reserva_reference="GYG-DEL-1"),
        headers=headers,
    )
    assert created.status_code == 201
    reserva_id = created.json()["id"]

    deleted = await auth_client.delete(f"/reservas/{reserva_id}", headers=headers)
    assert deleted.status_code == 204

    missing = await auth_client.get(f"/reservas/{reserva_id}", headers=headers)
    assert missing.status_code == 404

    listed = await auth_client.get("/reservas", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 0
    assert listed.json()["items"] == []


@pytest.mark.asyncio
async def test_delete_reserva_missing_returns_404(auth_client: AsyncClient) -> None:
    """Unknown or already-deleted UUID returns 404."""
    headers = await auth_headers(auth_client)
    response = await auth_client.delete(f"/reservas/{uuid4()}", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_reserva_unauthenticated_returns_401(
    auth_client: AsyncClient,
) -> None:
    """Missing Bearer token returns 401."""
    response = await auth_client.delete(f"/reservas/{uuid4()}")
    assert response.status_code == 401

"""Smoke tests for the scaffold health endpoint."""

from fastapi.testclient import TestClient

from vivecaribe.main import create_app


def test_health_returns_ok() -> None:
    """``GET /health`` returns 200 with status and version fields."""
    client = TestClient(create_app())
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body

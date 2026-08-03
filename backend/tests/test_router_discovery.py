"""Verify router auto-discovery finds capability modules."""

from fastapi.testclient import TestClient

from app.api.router import capability_router_ids
from app.main import app

client = TestClient(app)


def test_health_router_discovered() -> None:
    assert "health" in set(capability_router_ids())


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

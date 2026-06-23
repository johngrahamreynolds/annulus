from __future__ import annotations

from annulus_gateway.main import create_app
from fastapi.testclient import TestClient


def test_health_endpoint():
    app = create_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "annulus-gateway"
    assert "index" in data

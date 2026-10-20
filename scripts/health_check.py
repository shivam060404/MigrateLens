"""In-process smoke check; explicitly does not claim a listening HTTP server."""

from fastapi.testclient import TestClient
from src.api.app import create_app

with TestClient(create_app()) as client:
    live = client.get("/api/v1/health/live")
    assert live.status_code == 200, live.text
    assert live.json()["service"] == "migratelens-control"
    assert client.get("/api/v1/health/ready").status_code == 503
print("PASS: in-process API liveness; incomplete readiness correctly returns 503")

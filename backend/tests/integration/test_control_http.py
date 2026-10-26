"""HTTP and cryptographic identity contract with a labeled service double.

Database authorization requires the separate live PostgreSQL acceptance suite.
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.config.settings import Settings
from src.domain.control import AccessDenied, ControlUnavailable, NotFound
from src.infrastructure.identity.local_emulator import LocalIdentityEmulator


class ServiceDouble:
    def __init__(self, tenant):
        self.tenant = tenant
        self.received = []

    def events(self, principal, tenant, case_id, after, limit):
        self.received.append((principal.subject, tenant, case_id, after, limit))
        if tenant != self.tenant:
            raise AccessDenied("Repository action is not authorized")
        return {"items": [{"sequence": 3, "kind": "case.received"}], "next_cursor": 3}

    def case(self, principal, tenant, case_id):
        raise NotFound("Case not found")

    def download_artifact(self, principal, tenant, artifact_id):
        if tenant != self.tenant:
            raise AccessDenied("Repository action is not authorized")
        return b"synthetic artifact"


@pytest.fixture
def control(tmp_path):
    emulator = LocalIdentityEmulator(tmp_path / "keys", environment="test")
    public = emulator.initialize()
    settings = Settings(
        environment="test",
        auth_mode="local_token",
        control_api_enabled=True,
        identity_public_key_path=str(public),
        database_url="postgresql+psycopg2://runtime:local-only@localhost:55432/test",
    )
    app = create_app(settings)
    tenant = uuid4()
    service = ServiceDouble(tenant)
    app.state.control_service = service
    try:
        with TestClient(app) as client:
            yield client, emulator, service, tenant
    finally:
        app.state.control_engine.dispose()


def test_control_routes_require_real_signed_identity(control):
    client, emulator, _, tenant = control
    path = f"/api/v1/tenants/{tenant}/cases/{uuid4()}/events"
    assert client.get(path).status_code == 401
    assert client.get(path, headers={"Authorization": "Bearer invalid"}).status_code == 401
    token = emulator.issue("alice")
    response = client.get(path, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["next_cursor"] == 3


def test_tenant_and_cursor_are_forwarded_to_authorization_boundary(control):
    client, emulator, service, tenant = control
    case_id = uuid4()
    headers = {"Authorization": f"Bearer {emulator.issue('alice')}"}
    path = f"/api/v1/tenants/{tenant}/cases/{case_id}/events"
    assert client.get(path + "?after=2&limit=5", headers=headers).status_code == 200
    assert service.received == [("alice", tenant, case_id, 2, 5)]
    assert client.get(path + "?after=-1", headers=headers).status_code == 422
    assert (
        client.get(f"/api/v1/tenants/{uuid4()}/cases/{case_id}/events", headers=headers).status_code
        == 403
    )
    assert (
        client.get(f"/api/v1/tenants/{tenant}/cases/{case_id}", headers=headers).status_code == 404
    )


def test_control_api_is_off_without_configured_verifier():
    assert (
        create_app(Settings()).openapi()["paths"].get("/api/v1/tenants/{tenant_id}/cases") is None
    )
    with pytest.raises(ValueError, match="Control API requires"):
        Settings(control_api_enabled=True)
    with pytest.raises(ValueError, match="Production is gated"):
        Settings(environment="production", auth_mode="local_token", control_api_enabled=True)


def test_enabled_openapi_declares_bearer_security(control):
    client, _, _, _ = control
    schema = client.get("/openapi.json").json()
    operation = schema["paths"]["/api/v1/tenants/{tenant_id}/cases"]["post"]
    assert operation["security"] == [{"HTTPBearer": []}]
    assert schema["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"


def test_artifact_bytes_have_no_store_header(control):
    client, emulator, _, tenant = control
    headers = {"Authorization": f"Bearer {emulator.issue('alice')}"}
    artifact_id = uuid4()
    response = client.get(
        f"/api/v1/tenants/{tenant}/artifacts/{artifact_id}/download", headers=headers
    )
    assert response.status_code == 200
    assert response.content == b"synthetic artifact"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-type"] == "application/octet-stream"
    assert (
        client.get(
            f"/api/v1/tenants/{uuid4()}/artifacts/{artifact_id}/download", headers=headers
        ).status_code
        == 403
    )


def test_database_unavailable_has_safe_transport_error(control):
    client, emulator, service, tenant = control

    def unavailable(*args):
        raise ControlUnavailable("internal database detail")

    service.events = unavailable
    response = client.get(
        f"/api/v1/tenants/{tenant}/cases/{uuid4()}/events",
        headers={"Authorization": f"Bearer {emulator.issue('alice')}"},
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "Control database unavailable"}


def test_local_issuer_refuses_production_and_never_overwrites_keys(tmp_path):
    with pytest.raises(ValueError):
        LocalIdentityEmulator(tmp_path, environment="production")
    emulator = LocalIdentityEmulator(tmp_path, environment="test")
    emulator.initialize()
    with pytest.raises(FileExistsError):
        emulator.initialize()
    with pytest.raises(ValueError, match="lifetime"):
        emulator.issue("alice", ttl_seconds=901)

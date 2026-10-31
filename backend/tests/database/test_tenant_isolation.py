"""Strict live PostgreSQL gate. Never skipped or replaced with SQLite/doubles."""

import os
from uuid import uuid4

import pytest
import sqlalchemy as sa

from src.application.control import AttemptRequest, ControlService, CreateBinding, CreateCase
from src.config.database_gate import validate_test_database_urls
from src.domain.control import AccessDenied, Conflict, Principal
from src.infrastructure.persistence import schema as s
from src.infrastructure.persistence.database import Database
from src.infrastructure.persistence.repository import PostgresRepository


@pytest.fixture(scope="module")
def databases():
    if os.environ.get("ML_TEST_DATABASE_DISPOSABLE") != "yes":
        pytest.fail("Set ML_TEST_DATABASE_DISPOSABLE=yes for an isolated throwaway database")
    admin_url = os.environ.get("ML_TEST_ADMIN_DATABASE_URL")
    runtime_url = os.environ.get("ML_TEST_RUNTIME_DATABASE_URL")
    if not admin_url or not runtime_url:
        pytest.fail(
            "Set both ML_TEST_ADMIN_DATABASE_URL and ML_TEST_RUNTIME_DATABASE_URL for a disposable migrated PostgreSQL *_test database"
        )
    try:
        validate_test_database_urls(admin_url, runtime_url)
    except ValueError as exc:
        pytest.fail(str(exc))
    admin = sa.create_engine(admin_url, hide_parameters=True)
    runtime = sa.create_engine(runtime_url, hide_parameters=True)
    try:
        with admin.connect() as connection:
            role = connection.execute(
                sa.text("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user")
            ).scalar_one()
            assert role, "Test fixture provisioning requires an RLS-bypassing admin role"
            version = connection.execute(
                sa.text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            assert version == "0001_tenant_control"
            existing_tenants = connection.execute(
                sa.select(sa.func.count()).select_from(s.tenants)
            ).scalar_one()
            assert existing_tenants == 0, (
                "Live isolation tests require an empty disposable database"
            )
        yield admin, runtime
    finally:
        runtime.dispose()
        admin.dispose()


def test_rls_grants_and_pool_scope(databases):
    admin, runtime = databases
    tenant_a, tenant_b, repository_a, repository_ungranted, provider_a = (uuid4() for _ in range(5))
    with admin.begin() as connection:
        connection.execute(
            sa.insert(s.tenants),
            [
                {"tenant_id": tenant_a, "name": "Synthetic A"},
                {"tenant_id": tenant_b, "name": "Synthetic B"},
            ],
        )
        connection.execute(
            sa.insert(s.memberships),
            [
                {"tenant_id": tenant_a, "subject": "alice", "role": "owner"},
                {"tenant_id": tenant_b, "subject": "alice", "role": "owner"},
            ],
        )
        connection.execute(
            sa.insert(s.repositories),
            [
                {"tenant_id": tenant_a, "id": repository_a, "name": "Granted"},
                {"tenant_id": tenant_a, "id": repository_ungranted, "name": "Ungrant"},
            ],
        )
        connection.execute(
            sa.insert(s.grants).values(
                tenant_id=tenant_a, repository_id=repository_a, subject="alice"
            )
        )
        connection.execute(
            sa.insert(s.providers).values(
                tenant_id=tenant_a, id=provider_a, name="Fictional", classification="fictional"
            )
        )

    database = Database(runtime)
    with database.transaction(Principal("alice"), tenant_a) as (connection, _):
        assert (
            connection.execute(sa.select(sa.func.count()).select_from(s.tenants)).scalar_one() == 1
        )
        assert (
            connection.execute(sa.select(sa.func.count()).select_from(s.memberships)).scalar_one()
            == 1
        )
        assert (
            connection.execute(sa.select(sa.func.count()).select_from(s.repositories)).scalar_one()
            == 2
        )
    with runtime.connect() as connection:
        assert (
            connection.execute(sa.select(sa.func.count()).select_from(s.tenants)).scalar_one() == 0
        )
    with pytest.raises(AccessDenied):
        with database.transaction(Principal("bob"), tenant_a):
            pass

    service = ControlService(PostgresRepository(database))
    with pytest.raises(AccessDenied):
        service.create_binding(
            Principal("alice"),
            tenant_a,
            CreateBinding(
                repository_id=repository_ungranted, provider_id=provider_a, declared_version="v1"
            ),
        )
    binding = service.create_binding(
        Principal("alice"),
        tenant_a,
        CreateBinding(repository_id=repository_a, provider_id=provider_a, declared_version="v1"),
    )
    assert binding["tenant_id"] == tenant_a
    with database.transaction(Principal("alice"), tenant_b) as (connection, _):
        assert (
            connection.execute(sa.select(sa.func.count()).select_from(s.bindings)).scalar_one() == 0
        )
        assert (
            connection.execute(sa.select(sa.func.count()).select_from(s.memberships)).scalar_one()
            == 1
        )

    case = service.create_case(
        Principal("alice"),
        tenant_a,
        CreateCase(
            binding_id=binding["id"],
            base_sha="a" * 40,
            old_contract_hash="b" * 64,
            new_contract_hash="c" * 64,
        ),
    )
    with admin.begin() as connection:
        connection.execute(sa.insert(s.budgets).values(tenant_id=tenant_a, limit_microusd=500))
        connection.execute(
            sa.update(s.cases)
            .where(s.cases.c.tenant_id == tenant_a, s.cases.c.id == case["id"])
            .values(state="READY_TO_REPAIR")
        )
    request = AttemptRequest(expected_version=case["version"], estimate_microusd=400)
    job = service.queue_attempt(Principal("alice"), tenant_a, case["id"], request)
    assert job["attempt"] == 1 and job["state"] == "QUEUED"
    with pytest.raises(Conflict):
        service.queue_attempt(Principal("alice"), tenant_a, case["id"], request)
    with pytest.raises(Conflict, match="already active"):
        service.queue_attempt(
            Principal("alice"),
            tenant_a,
            case["id"],
            AttemptRequest(expected_version=case["version"] + 1, estimate_microusd=1),
        )
    with database.transaction(Principal("alice"), tenant_a) as (connection, _):
        assert connection.execute(sa.select(s.budgets.c.reserved_microusd)).scalar_one() == 400
        assert (
            connection.execute(sa.select(sa.func.count()).select_from(s.reservations)).scalar_one()
            == 1
        )
        assert (
            connection.execute(sa.select(sa.func.count()).select_from(s.outbox)).scalar_one() == 2
        )

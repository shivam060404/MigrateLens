"""Role admission unit tests; live PostgreSQL remains a separate acceptance gate."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.domain.control import AccessDenied, Principal
from src.infrastructure.persistence.database import (
    Database,
    assert_runtime_role,
    assert_runtime_schema,
)
from src.infrastructure.persistence.schema import metadata


def connection_with_role(**overrides):
    connection = MagicMock()
    connection.execute.return_value.mappings.return_value.one.return_value = {
        "privileged": False,
        "switched": False,
        "owns_tables": False,
        **overrides,
    }
    return connection


@pytest.mark.parametrize("flag", ["privileged", "switched", "owns_tables"])
def test_role_rejection_precedes_identity_and_membership_queries(flag):
    connection = connection_with_role(**{flag: True})
    engine = MagicMock()
    engine.dialect.name = "postgresql"
    engine.begin.return_value.__enter__.return_value = connection
    with pytest.raises(AccessDenied):
        with Database(engine).transaction(Principal("alice"), uuid4()):
            pytest.fail("Privileged connection reached tenant operations")
    assert connection.execute.call_count == 1


def test_restricted_role_admitted():
    assert_runtime_role(connection_with_role())


@pytest.mark.parametrize("defect", ["missing", "rls_off", "not_forced", "no_policy"])
def test_schema_admission_rejects_missing_protection(defect):
    rows = [
        {
            "relname": table.name,
            "relrowsecurity": True,
            "relforcerowsecurity": True,
            "tenant_policy": True,
        }
        for table in metadata.tables.values()
    ]
    if defect == "missing":
        rows.pop()
    else:
        key = {
            "rls_off": "relrowsecurity",
            "not_forced": "relforcerowsecurity",
            "no_policy": "tenant_policy",
        }[defect]
        rows[0][key] = False
    connection = MagicMock()
    connection.execute.return_value.mappings.return_value.all.return_value = rows
    with pytest.raises(AccessDenied, match="forced tenant policies"):
        assert_runtime_schema(connection)


def test_schema_admission_accepts_declared_forced_tables():
    rows = [
        {
            "relname": table.name,
            "relrowsecurity": True,
            "relforcerowsecurity": True,
            "tenant_policy": True,
        }
        for table in metadata.tables.values()
    ]
    connection = MagicMock()
    connection.execute.return_value.mappings.return_value.all.return_value = rows
    assert_runtime_schema(connection)


def test_startup_rejects_bad_role_and_disposes_engine(tmp_path, monkeypatch):
    from src.bootstrap import create_control_plane
    from src.config.settings import Settings
    from src.infrastructure.identity.local_emulator import LocalIdentityEmulator

    public = LocalIdentityEmulator(tmp_path / "keys", environment="test").initialize()
    engine = MagicMock()
    engine.dialect.name = "postgresql"
    engine.connect.return_value.__enter__.return_value = connection_with_role(privileged=True)
    monkeypatch.setattr("sqlalchemy.create_engine", lambda *args, **kwargs: engine)
    settings = Settings(
        environment="test",
        control_api_enabled=True,
        auth_mode="local_token",
        identity_public_key_path=str(public),
        database_url="postgresql+psycopg2://runtime@localhost/MigrateLens",
    )
    with pytest.raises(AccessDenied):
        create_control_plane(settings)
    engine.dispose.assert_called_once()

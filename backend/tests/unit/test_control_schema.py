"""Offline DDL checks, explicitly not a substitute for live PostgreSQL RLS tests."""

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from src.config.paths import ROOT
from src.infrastructure.persistence.schema import metadata


def test_frozen_migration_matches_table_definitions_and_forces_rls():
    sql = (ROOT / "backend/migrations/versions/0001_tenant_control.sql").read_text()
    assert sql.index("CREATE POLICY") > sql.rindex("CREATE TABLE")
    for table in metadata.sorted_tables:
        assert str(CreateTable(table).compile(dialect=postgresql.dialect())).strip() in sql
        assert f"ALTER TABLE ml.{table.name} ENABLE ROW LEVEL SECURITY;" in sql
        assert f"ALTER TABLE ml.{table.name} FORCE ROW LEVEL SECURITY;" in sql
        assert "tenant_id" in table.primary_key.columns
        for constraint in table.foreign_key_constraints:
            assert "tenant_id" in constraint.column_keys


def test_runtime_cannot_mutate_authority_or_erase_audit():
    sql = (ROOT / "backend/migrations/versions/0001_tenant_control.sql").read_text()
    grants = [line for line in sql.splitlines() if line.startswith("GRANT")]
    assert not any("DELETE" in line or "TRUNCATE" in line or "ALL" in line for line in grants)
    for table in ["memberships", "repository_grants", "repositories", "providers"]:
        assert f"GRANT SELECT ON ml.{table} TO ml_runtime;" in grants
        assert sum(f"ml.{table} " in line for line in grants) == 1
    assert "GRANT SELECT, INSERT ON ml.audit_events TO ml_runtime;" in grants


def test_membership_policy_scopes_after_identity_lookup():
    sql = (ROOT / "backend/migrations/versions/0001_tenant_control.sql").read_text()
    policy = next(
        line
        for line in sql.splitlines()
        if line.startswith("CREATE POLICY tenant_scope ON ml.memberships")
    )
    assert "subject = current_setting('ml.subject', true) AND active" in policy
    assert policy.count("tenant_id = NULLIF(current_setting('ml.tenant_id', true), '')::uuid") == 2

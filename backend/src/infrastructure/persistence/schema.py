"""PostgreSQL relational metadata. Every child ownership edge is tenant-composite."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

metadata = sa.MetaData(
    schema="ml",
    naming_convention={
        "pk": "pk_%(table_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ix": "ix_%(table_name)s_%(column_0_name)s",
    },
)


def tenant_column():
    return sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, primary_key=True)


def identity_column():
    return sa.Column("id", UUID(as_uuid=True), nullable=False, primary_key=True)


def timestamp():
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


def parent(table, *columns):
    return sa.ForeignKeyConstraint(
        ["tenant_id", *columns], [f"ml.{table}.tenant_id", *[f"ml.{table}.id" for _ in columns]]
    )


tenants = sa.Table(
    "tenants",
    metadata,
    tenant_column(),
    sa.Column("name", sa.String(100), nullable=False),
    timestamp(),
)
memberships = sa.Table(
    "memberships",
    metadata,
    tenant_column(),
    sa.Column("subject", sa.String(128), primary_key=True),
    sa.Column("role", sa.String(20), nullable=False),
    sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
    timestamp(),
    sa.ForeignKeyConstraint(["tenant_id"], ["ml.tenants.tenant_id"]),
    sa.CheckConstraint(
        "role IN ('owner','maintainer','reviewer','viewer','worker')", name="membership_role"
    ),
)
repositories = sa.Table(
    "repositories",
    metadata,
    tenant_column(),
    identity_column(),
    sa.Column("name", sa.String(200), nullable=False),
    sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.true()),
    timestamp(),
    sa.ForeignKeyConstraint(["tenant_id"], ["ml.tenants.tenant_id"]),
)
grants = sa.Table(
    "repository_grants",
    metadata,
    tenant_column(),
    sa.Column("repository_id", UUID(as_uuid=True), primary_key=True),
    sa.Column("subject", sa.String(128), primary_key=True),
    timestamp(),
    parent("repositories", "repository_id"),
    sa.ForeignKeyConstraint(
        ["tenant_id", "subject"], ["ml.memberships.tenant_id", "ml.memberships.subject"]
    ),
)
providers = sa.Table(
    "providers",
    metadata,
    tenant_column(),
    identity_column(),
    sa.Column("name", sa.String(100), nullable=False),
    sa.Column("classification", sa.String(30), nullable=False),
    timestamp(),
    sa.ForeignKeyConstraint(["tenant_id"], ["ml.tenants.tenant_id"]),
    sa.CheckConstraint(
        "classification IN ('fictional','internal_test')", name="provider_test_only"
    ),
)
bindings = sa.Table(
    "bindings",
    metadata,
    tenant_column(),
    identity_column(),
    sa.Column("repository_id", UUID(as_uuid=True), nullable=False),
    sa.Column("provider_id", UUID(as_uuid=True), nullable=False),
    sa.Column("declared_version", sa.String(100), nullable=False),
    timestamp(),
    parent("repositories", "repository_id"),
    parent("providers", "provider_id"),
    sa.UniqueConstraint("tenant_id", "repository_id", "id", name="uq_binding_repository"),
)
cases = sa.Table(
    "cases",
    metadata,
    tenant_column(),
    identity_column(),
    sa.Column("repository_id", UUID(as_uuid=True), nullable=False),
    sa.Column("binding_id", UUID(as_uuid=True), nullable=False),
    sa.Column("identity_hash", sa.String(64), nullable=False),
    sa.Column("base_sha", sa.String(40), nullable=False),
    sa.Column("old_contract_hash", sa.String(64), nullable=False),
    sa.Column("new_contract_hash", sa.String(64), nullable=False),
    sa.Column("policy_hash", sa.String(64), nullable=False),
    sa.Column("revision", sa.Integer, nullable=False, server_default="1"),
    sa.Column("version", sa.Integer, nullable=False, server_default="1"),
    sa.Column("state", sa.String(30), nullable=False, server_default="RECEIVED"),
    sa.Column("cancel_requested", sa.Boolean, nullable=False, server_default=sa.false()),
    sa.Column("verdict", sa.String(40)),
    timestamp(),
    sa.ForeignKeyConstraint(
        ["tenant_id", "repository_id", "binding_id"],
        ["ml.bindings.tenant_id", "ml.bindings.repository_id", "ml.bindings.id"],
    ),
    sa.UniqueConstraint("tenant_id", "repository_id", "id", name="uq_case_repository"),
    sa.UniqueConstraint("tenant_id", "binding_id", "identity_hash", name="uq_case_identity"),
    sa.CheckConstraint("revision > 0 AND version > 0", name="case_versions"),
    sa.CheckConstraint(
        "state IN ('RECEIVED','ANALYZING','WAITING_FOR_INPUT','READY_TO_REPAIR','REPAIRING','VALIDATING','AWAITING_REVIEW','PUBLISHING','PUBLISHED','COMPLETED','FAILED','CANCELLED')",
        name="case_state",
    ),
)
events = sa.Table(
    "case_events",
    metadata,
    tenant_column(),
    sa.Column("case_id", UUID(as_uuid=True), primary_key=True),
    sa.Column("sequence", sa.Integer, primary_key=True),
    sa.Column("kind", sa.String(80), nullable=False),
    sa.Column("payload", JSONB, nullable=False),
    timestamp(),
    parent("cases", "case_id"),
)
audit = sa.Table(
    "audit_events",
    metadata,
    tenant_column(),
    identity_column(),
    sa.Column("subject", sa.String(128), nullable=False),
    sa.Column("action", sa.String(80), nullable=False),
    sa.Column("resource_id", UUID(as_uuid=True), nullable=False),
    sa.Column("correlation_id", UUID(as_uuid=True), nullable=False),
    timestamp(),
    sa.ForeignKeyConstraint(["tenant_id"], ["ml.tenants.tenant_id"]),
)
jobs = sa.Table(
    "jobs",
    metadata,
    tenant_column(),
    identity_column(),
    sa.Column("case_id", UUID(as_uuid=True), nullable=False),
    sa.Column("attempt", sa.Integer, nullable=False),
    sa.Column("state", sa.String(20), nullable=False, server_default="QUEUED"),
    timestamp(),
    parent("cases", "case_id"),
    sa.UniqueConstraint("tenant_id", "case_id", "attempt", name="uq_case_attempt"),
    sa.CheckConstraint("attempt BETWEEN 1 AND 3", name="attempt_bounds"),
    sa.CheckConstraint(
        "state IN ('QUEUED','RUNNING','COMPLETED','FAILED','CANCELLED')", name="job_state"
    ),
)
budgets = sa.Table(
    "budgets",
    metadata,
    tenant_column(),
    sa.Column("limit_microusd", sa.BigInteger, nullable=False),
    sa.Column("reserved_microusd", sa.BigInteger, nullable=False, server_default="0"),
    sa.Column("spent_microusd", sa.BigInteger, nullable=False, server_default="0"),
    sa.ForeignKeyConstraint(["tenant_id"], ["ml.tenants.tenant_id"]),
    sa.CheckConstraint(
        "limit_microusd >= 0 AND reserved_microusd >= 0 AND spent_microusd >= 0",
        name="nonnegative_budget",
    ),
)
reservations = sa.Table(
    "reservations",
    metadata,
    tenant_column(),
    identity_column(),
    sa.Column("job_id", UUID(as_uuid=True), nullable=False),
    sa.Column("estimate_microusd", sa.BigInteger, nullable=False),
    sa.Column("actual_microusd", sa.BigInteger),
    sa.Column("settled", sa.Boolean, nullable=False, server_default=sa.false()),
    timestamp(),
    parent("jobs", "job_id"),
    sa.UniqueConstraint("tenant_id", "job_id", name="uq_job_reservation"),
    sa.CheckConstraint(
        "estimate_microusd > 0 AND (actual_microusd IS NULL OR actual_microusd >= 0)",
        name="reservation_amounts",
    ),
)
outbox = sa.Table(
    "outbox",
    metadata,
    tenant_column(),
    identity_column(),
    sa.Column("case_id", UUID(as_uuid=True), nullable=False),
    sa.Column("case_version", sa.Integer, nullable=False),
    sa.Column("kind", sa.String(80), nullable=False),
    sa.Column("state", sa.String(20), nullable=False, server_default="PENDING"),
    sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
    sa.Column(
        "available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    ),
    sa.Column("lease_until", sa.DateTime(timezone=True)),
    timestamp(),
    parent("cases", "case_id"),
    sa.UniqueConstraint("tenant_id", "case_id", "case_version", "kind", name="uq_outbox_event"),
    sa.CheckConstraint("attempts BETWEEN 0 AND 3", name="dispatch_attempts"),
    sa.CheckConstraint("state IN ('PENDING','LEASED','DELIVERED','DEAD')", name="outbox_state"),
)
artifacts = sa.Table(
    "artifacts",
    metadata,
    tenant_column(),
    identity_column(),
    sa.Column("case_id", UUID(as_uuid=True), nullable=False),
    sa.Column("sha256", sa.String(64), nullable=False),
    sa.Column("size_bytes", sa.BigInteger, nullable=False),
    sa.Column("object_key", sa.String(300), nullable=False),
    timestamp(),
    parent("cases", "case_id"),
    sa.UniqueConstraint("tenant_id", "object_key", name="uq_artifact_object"),
    sa.CheckConstraint("size_bytes BETWEEN 0 AND 10000000", name="artifact_size"),
)

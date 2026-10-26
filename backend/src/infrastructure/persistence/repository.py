"""SQL implementation of the control-plane port; each operation shares one transaction."""

from contextlib import contextmanager
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import OperationalError, ProgrammingError

from src.domain.control import (
    BudgetExceeded,
    Conflict,
    ControlUnavailable,
    Membership,
    Principal,
    reserve_budget,
)
from src.infrastructure.persistence.database import Database
from src.infrastructure.persistence import schema as s


class PostgresSession:
    def __init__(self, connection, membership: Membership):
        self.connection = connection
        self.membership = membership
        self.tenant = membership.tenant_id

    def _one(self, query):
        row = self.connection.execute(query).mappings().one_or_none()
        return dict(row) if row is not None else None

    def _list(self, query):
        return [dict(row) for row in self.connection.execute(query).mappings()]

    def repository_granted(self, repository_id: UUID) -> bool:
        return (
            self.connection.execute(
                sa.select(s.grants.c.repository_id)
                .join(
                    s.repositories,
                    sa.and_(
                        s.repositories.c.tenant_id == s.grants.c.tenant_id,
                        s.repositories.c.id == s.grants.c.repository_id,
                    ),
                )
                .where(
                    s.grants.c.tenant_id == self.tenant,
                    s.grants.c.subject == self.membership.subject,
                    s.grants.c.repository_id == repository_id,
                    s.repositories.c.enabled.is_(True),
                )
            ).first()
            is not None
        )

    def binding(self, binding_id: UUID):
        return self._one(
            sa.select(s.bindings).where(
                s.bindings.c.tenant_id == self.tenant, s.bindings.c.id == binding_id
            )
        )

    def provider_exists(self, provider_id: UUID):
        return (
            self._one(
                sa.select(s.providers.c.id).where(
                    s.providers.c.tenant_id == self.tenant, s.providers.c.id == provider_id
                )
            )
            is not None
        )

    def insert_binding(self, data: dict):
        row = self._one(sa.insert(s.bindings).values(**data).returning(s.bindings))
        self._audit("binding.created", data["id"])
        return row

    def list_bindings(self, repository_id: UUID, limit: int):
        return self._list(
            sa.select(s.bindings)
            .where(
                s.bindings.c.tenant_id == self.tenant, s.bindings.c.repository_id == repository_id
            )
            .order_by(s.bindings.c.created_at, s.bindings.c.id)
            .limit(limit)
        )

    def case(self, case_id: UUID):
        return self._one(
            sa.select(s.cases).where(s.cases.c.tenant_id == self.tenant, s.cases.c.id == case_id)
        )

    def list_cases(self, repository_id: UUID, limit: int):
        return self._list(
            sa.select(s.cases)
            .where(s.cases.c.tenant_id == self.tenant, s.cases.c.repository_id == repository_id)
            .order_by(s.cases.c.created_at, s.cases.c.id)
            .limit(limit)
        )

    def _audit(self, action: str, resource: UUID):
        self.connection.execute(
            sa.insert(s.audit).values(
                tenant_id=self.tenant,
                id=uuid4(),
                subject=self.membership.subject,
                action=action,
                resource_id=resource,
                correlation_id=uuid4(),
            )
        )

    def _event(self, row: dict, kind: str):
        self.connection.execute(
            sa.insert(s.events).values(
                tenant_id=self.tenant,
                case_id=row["id"],
                sequence=row["version"],
                kind=kind,
                payload={
                    "state": row["state"],
                    "revision": row["revision"],
                    "cancel_requested": row["cancel_requested"],
                },
            )
        )
        self.connection.execute(
            sa.insert(s.outbox).values(
                tenant_id=self.tenant,
                id=uuid4(),
                case_id=row["id"],
                case_version=row["version"],
                kind=kind,
            )
        )
        self._audit(kind, row["id"])

    def insert_case(self, data: dict):
        row = self._one(
            insert(s.cases)
            .values(**data)
            .on_conflict_do_nothing(constraint="uq_case_identity")
            .returning(s.cases)
        )
        if row is None:
            return self._one(
                sa.select(s.cases).where(
                    s.cases.c.tenant_id == self.tenant,
                    s.cases.c.binding_id == data["binding_id"],
                    s.cases.c.identity_hash == data["identity_hash"],
                )
            )
        self._event(row, "case.received")
        return row

    def cancel_case(self, case_id: UUID, version: int, immediate: bool):
        values: dict[str, object] = {"cancel_requested": True, "version": version + 1}
        if immediate:
            values["state"] = "CANCELLED"
        row = self._one(
            sa.update(s.cases)
            .where(
                s.cases.c.tenant_id == self.tenant,
                s.cases.c.id == case_id,
                s.cases.c.version == version,
            )
            .values(**values)
            .returning(s.cases)
        )
        if row is None:
            raise Conflict("Concurrent case modification")
        self._event(row, "case.cancel_requested")
        return row

    def reserve_attempt(self, case_id: UUID, version: int, estimate: int):
        case = self._one(
            sa.select(s.cases)
            .where(s.cases.c.tenant_id == self.tenant, s.cases.c.id == case_id)
            .with_for_update()
        )
        if (
            case is None
            or case["version"] != version
            or case["state"] != "READY_TO_REPAIR"
            or case["cancel_requested"]
        ):
            raise Conflict("Concurrent case modification or case not ready")
        budget = self._one(
            sa.select(s.budgets).where(s.budgets.c.tenant_id == self.tenant).with_for_update()
        )
        if budget is None:
            raise BudgetExceeded("Tenant budget is not configured")
        attempts = self.connection.execute(
            sa.select(sa.func.count())
            .select_from(s.jobs)
            .where(s.jobs.c.tenant_id == self.tenant, s.jobs.c.case_id == case_id)
        ).scalar_one()
        active = self.connection.execute(
            sa.select(sa.func.count())
            .select_from(s.jobs)
            .where(
                s.jobs.c.tenant_id == self.tenant,
                s.jobs.c.case_id == case_id,
                s.jobs.c.state.in_(["QUEUED", "RUNNING"]),
            )
        ).scalar_one()
        if active:
            raise Conflict("A repair attempt is already active")
        reserve_budget(
            budget["limit_microusd"],
            budget["spent_microusd"],
            budget["reserved_microusd"],
            estimate,
            attempts,
        )
        job_id = uuid4()
        job = self._one(
            sa.insert(s.jobs)
            .values(tenant_id=self.tenant, id=job_id, case_id=case_id, attempt=attempts + 1)
            .returning(s.jobs)
        )
        self.connection.execute(
            sa.update(s.budgets)
            .where(s.budgets.c.tenant_id == self.tenant)
            .values(reserved_microusd=budget["reserved_microusd"] + estimate)
        )
        self.connection.execute(
            sa.insert(s.reservations).values(
                tenant_id=self.tenant,
                id=uuid4(),
                job_id=job_id,
                estimate_microusd=estimate,
            )
        )
        updated = self._one(
            sa.update(s.cases)
            .where(
                s.cases.c.tenant_id == self.tenant,
                s.cases.c.id == case_id,
                s.cases.c.version == version,
            )
            .values(version=version + 1)
            .returning(s.cases)
        )
        if updated is None:
            raise Conflict("Concurrent case modification")
        self._event(updated, "attempt.queued")
        return job

    def events(self, case_id: UUID, after: int, limit: int):
        return self._list(
            sa.select(s.events)
            .where(
                s.events.c.tenant_id == self.tenant,
                s.events.c.case_id == case_id,
                s.events.c.sequence > after,
            )
            .order_by(s.events.c.sequence)
            .limit(limit)
        )

    def jobs(self, case_id: UUID, limit: int):
        return self._list(
            sa.select(s.jobs)
            .where(s.jobs.c.tenant_id == self.tenant, s.jobs.c.case_id == case_id)
            .order_by(s.jobs.c.attempt)
            .limit(limit)
        )

    def artifact(self, artifact_id: UUID):
        return self._one(
            sa.select(s.artifacts).where(
                s.artifacts.c.tenant_id == self.tenant, s.artifacts.c.id == artifact_id
            )
        )


class PostgresRepository:
    def __init__(self, database: Database):
        self.database = database

    @contextmanager
    def session(self, principal: Principal, tenant_id: UUID):
        try:
            with self.database.transaction(principal, tenant_id) as (connection, membership):
                yield PostgresSession(connection, membership)
        except (OperationalError, ProgrammingError) as exc:
            raise ControlUnavailable("Control database unavailable") from exc

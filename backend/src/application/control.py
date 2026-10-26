"""Authenticated metadata operations. This service cannot execute or publish repairs."""

from contextlib import AbstractContextManager
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import Field

from src.domain.control import Conflict, Membership, NotFound, Principal, TRANSITIONS, authorize
from src.domain.models import Policy, Strict, digest


class CreateBinding(Strict):
    repository_id: UUID
    provider_id: UUID
    declared_version: str = Field(min_length=1, max_length=100)


class CreateCase(Strict):
    binding_id: UUID
    base_sha: str = Field(pattern=r"^[a-f0-9]{40}$")
    old_contract_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    new_contract_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class CancelCase(Strict):
    expected_version: int = Field(ge=1)


class AttemptRequest(Strict):
    expected_version: int = Field(ge=1)
    estimate_microusd: int = Field(gt=0, le=9_223_372_036_854_775_807)


class ControlSession(Protocol):
    membership: Membership

    def repository_granted(self, repository_id: UUID) -> bool: ...
    def binding(self, binding_id: UUID) -> dict | None: ...
    def provider_exists(self, provider_id: UUID) -> bool: ...
    def insert_binding(self, data: dict) -> dict: ...
    def list_bindings(self, repository_id: UUID, limit: int) -> list[dict]: ...
    def case(self, case_id: UUID) -> dict | None: ...
    def list_cases(self, repository_id: UUID, limit: int) -> list[dict]: ...
    def insert_case(self, data: dict) -> dict: ...
    def cancel_case(self, case_id: UUID, version: int, immediate: bool) -> dict: ...
    def reserve_attempt(self, case_id: UUID, version: int, estimate: int) -> dict: ...
    def events(self, case_id: UUID, after: int, limit: int) -> list[dict]: ...
    def jobs(self, case_id: UUID, limit: int) -> list[dict]: ...
    def artifact(self, artifact_id: UUID) -> dict | None: ...


class ControlRepository(Protocol):
    def session(
        self, principal: Principal, tenant_id: UUID
    ) -> AbstractContextManager[ControlSession]: ...


class ArtifactReader(Protocol):
    def read(self, tenant: UUID, artifact_id: UUID, key: str, sha256: str, size: int) -> bytes: ...


class ControlService:
    def __init__(
        self,
        repository: ControlRepository,
        *,
        artifact_reader: ArtifactReader | None = None,
        emergency_stop: bool = False,
    ):
        self.repository = repository
        self.artifact_reader = artifact_reader
        self.emergency_stop = emergency_stop

    @staticmethod
    def _access(session: ControlSession, repository_id: UUID, action: str):
        authorize(session.membership, session.repository_granted(repository_id), action)

    @staticmethod
    def _case(session: ControlSession, case_id: UUID) -> dict:
        row = session.case(case_id)
        if row is None:
            raise NotFound("Case not found")
        return row

    def create_binding(self, principal: Principal, tenant: UUID, request: CreateBinding) -> dict:
        if self.emergency_stop:
            raise Conflict("Emergency stop active")
        with self.repository.session(principal, tenant) as session:
            self._access(session, request.repository_id, "create")
            if not session.provider_exists(request.provider_id):
                raise NotFound("Registered test provider not found")
            return session.insert_binding(
                {**request.model_dump(), "id": uuid4(), "tenant_id": tenant}
            )

    def bindings(self, principal: Principal, tenant: UUID, repository_id: UUID, limit: int = 50):
        with self.repository.session(principal, tenant) as session:
            self._access(session, repository_id, "read")
            return session.list_bindings(repository_id, min(max(limit, 1), 100))

    def create_case(self, principal: Principal, tenant: UUID, request: CreateCase) -> dict:
        if self.emergency_stop:
            raise Conflict("Emergency stop active")
        with self.repository.session(principal, tenant) as session:
            binding = session.binding(request.binding_id)
            if binding is None:
                raise NotFound("Binding not found")
            self._access(session, binding["repository_id"], "create")
            policy_hash = digest(Policy().model_dump(mode="json"))
            identity = digest(
                {
                    **request.model_dump(mode="json"),
                    "tenant": str(tenant),
                    "policy": policy_hash,
                    "revision": 1,
                }
            )
            return session.insert_case(
                {
                    **request.model_dump(),
                    "id": uuid4(),
                    "tenant_id": tenant,
                    "repository_id": binding["repository_id"],
                    "policy_hash": policy_hash,
                    "identity_hash": identity,
                }
            )

    def cases(self, principal: Principal, tenant: UUID, repository_id: UUID, limit: int = 50):
        with self.repository.session(principal, tenant) as session:
            self._access(session, repository_id, "read")
            return session.list_cases(repository_id, min(max(limit, 1), 100))

    def case(self, principal: Principal, tenant: UUID, case_id: UUID):
        with self.repository.session(principal, tenant) as session:
            row = self._case(session, case_id)
            self._access(session, row["repository_id"], "read")
            return row

    def cancel(self, principal: Principal, tenant: UUID, case_id: UUID, request: CancelCase):
        with self.repository.session(principal, tenant) as session:
            row = self._case(session, case_id)
            self._access(session, row["repository_id"], "cancel")
            if row["version"] != request.expected_version:
                raise Conflict("Stale case version")
            if row["cancel_requested"]:
                return row
            if not TRANSITIONS.get(row["state"]):
                raise Conflict("Terminal cases require a new revision")
            immediate = "CANCELLED" in TRANSITIONS[row["state"]] and row["state"] not in {
                "REPAIRING",
                "VALIDATING",
            }
            return session.cancel_case(case_id, request.expected_version, immediate)

    def queue_attempt(
        self, principal: Principal, tenant: UUID, case_id: UUID, request: AttemptRequest
    ):
        """Internal only until a durable worker consumes queued jobs."""
        if self.emergency_stop:
            raise Conflict("Emergency stop active")
        with self.repository.session(principal, tenant) as session:
            row = self._case(session, case_id)
            self._access(session, row["repository_id"], "create")
            if (
                row["version"] != request.expected_version
                or row["state"] != "READY_TO_REPAIR"
                or row["cancel_requested"]
            ):
                raise Conflict("Case is not ready at the requested version")
            return session.reserve_attempt(
                case_id, request.expected_version, request.estimate_microusd
            )

    def events(
        self, principal: Principal, tenant: UUID, case_id: UUID, after: int = 0, limit: int = 100
    ):
        if after < 0 or not 1 <= limit <= 100:
            raise ValueError("Invalid event cursor or page size")
        with self.repository.session(principal, tenant) as session:
            row = self._case(session, case_id)
            self._access(session, row["repository_id"], "read")
            items = session.events(case_id, after, limit)
            return {"items": items, "next_cursor": items[-1]["sequence"] if items else after}

    def jobs(self, principal: Principal, tenant: UUID, case_id: UUID):
        with self.repository.session(principal, tenant) as session:
            row = self._case(session, case_id)
            self._access(session, row["repository_id"], "read")
            return session.jobs(case_id, 100)

    def artifact(self, principal: Principal, tenant: UUID, artifact_id: UUID):
        with self.repository.session(principal, tenant) as session:
            artifact = session.artifact(artifact_id)
            if artifact is None:
                raise NotFound("Artifact not found")
            row = self._case(session, artifact["case_id"])
            self._access(session, row["repository_id"], "read")
            # Raw object keys are never API responses or publication metadata.
            return {
                key: artifact[key]
                for key in ["id", "case_id", "sha256", "size_bytes", "created_at"]
            }

    def download_artifact(self, principal: Principal, tenant: UUID, artifact_id: UUID) -> bytes:
        if self.artifact_reader is None:
            raise Conflict("Artifact storage is not configured")
        with self.repository.session(principal, tenant) as session:
            artifact = session.artifact(artifact_id)
            if artifact is None:
                raise NotFound("Artifact not found")
            row = self._case(session, artifact["case_id"])
            self._access(session, row["repository_id"], "read")
            return self.artifact_reader.read(
                tenant,
                artifact_id,
                artifact["object_key"],
                artifact["sha256"],
                artifact["size_bytes"],
            )

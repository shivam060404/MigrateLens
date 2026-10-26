"""Pure policy and application-port tests; these do not prove database isolation."""

from contextlib import contextmanager
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.application.control import AttemptRequest, CancelCase, ControlService, CreateCase
from src.domain.control import (
    AccessDenied,
    BudgetExceeded,
    Conflict,
    Membership,
    Principal,
    Role,
    authorize,
    reserve_budget,
    transition,
)


@pytest.mark.parametrize("role", list(Role))
def test_explicit_repository_grant_required_even_for_owner(role):
    with pytest.raises(AccessDenied):
        authorize(Membership(uuid4(), "alice", role), False, "read")


@pytest.mark.parametrize("role", [Role.VIEWER, Role.REVIEWER, Role.WORKER])
def test_read_roles_cannot_create_cases(role):
    with pytest.raises(AccessDenied):
        authorize(Membership(uuid4(), "alice", role), True, "create")


def test_worker_execution_is_separate_from_owner_permissions():
    with pytest.raises(AccessDenied):
        authorize(Membership(uuid4(), "alice", Role.OWNER), True, "execute")
    authorize(Membership(uuid4(), "worker", Role.WORKER), True, "execute")


@pytest.mark.parametrize("state", ["PUBLISHED", "COMPLETED", "FAILED", "CANCELLED", "UNKNOWN"])
def test_terminal_or_unknown_states_cannot_restart(state):
    with pytest.raises(Conflict):
        transition(state, "ANALYZING", revision_changed=True)


def test_reanalysis_requires_evidence_revision():
    with pytest.raises(Conflict):
        transition("AWAITING_REVIEW", "ANALYZING")
    transition("AWAITING_REVIEW", "ANALYZING", revision_changed=True)


@pytest.mark.parametrize("estimate,attempts", [(31, 0), (1, 3)])
def test_reservations_include_existing_spend_and_attempt_limit(estimate, attempts):
    with pytest.raises(BudgetExceeded):
        reserve_budget(100, 50, 20, estimate, attempts)
    reserve_budget(100, 50, 20, 30, 2)


class MemoryPort:
    """Explicit service double; no persistence or concurrency claims."""

    def __init__(self):
        self.tenant = uuid4()
        self.membership = Membership(self.tenant, "alice", Role.OWNER)
        self.repo = uuid4()
        self.granted = True
        self.row = {
            "id": uuid4(),
            "repository_id": self.repo,
            "version": 2,
            "revision": 1,
            "state": "RECEIVED",
            "cancel_requested": False,
        }
        self.writes = []

    @contextmanager
    def session(self, principal, tenant):
        if tenant != self.tenant or principal.subject != self.membership.subject:
            raise AccessDenied("Membership required")
        yield self

    def repository_granted(self, repository_id):
        return self.granted and repository_id == self.repo

    def binding(self, binding_id):
        return {"repository_id": self.repo}

    def case(self, case_id):
        return self.row if case_id == self.row["id"] else None

    def insert_case(self, data):
        self.writes.append(data)
        return data

    def cancel_case(self, case_id, version, immediate):
        self.writes.append((case_id, version, immediate))
        return self.row

    def reserve_attempt(self, case_id, version, estimate):
        self.writes.append((case_id, version, estimate))
        return {"case_id": case_id, "attempt": 1}


def test_case_identity_is_stable_and_server_binds_policy():
    port = MemoryPort()
    service = ControlService(port)
    request = CreateCase(
        binding_id=uuid4(),
        base_sha="a" * 40,
        old_contract_hash="b" * 64,
        new_contract_hash="c" * 64,
    )
    first = service.create_case(Principal("alice"), port.tenant, request)
    second = service.create_case(Principal("alice"), port.tenant, request)
    assert first["identity_hash"] == second["identity_hash"]
    assert len(first["policy_hash"]) == 64
    assert first["tenant_id"] == port.tenant
    port.granted = False
    with pytest.raises(AccessDenied):
        service.create_case(Principal("alice"), port.tenant, request)
    assert len(port.writes) == 2


def test_cancel_stale_version_does_not_write():
    port = MemoryPort()
    with pytest.raises(Conflict):
        ControlService(port).cancel(
            Principal("alice"), port.tenant, port.row["id"], CancelCase(expected_version=1)
        )
    assert not port.writes


@pytest.mark.parametrize(
    "state,immediate", [("RECEIVED", True), ("REPAIRING", False), ("VALIDATING", False)]
)
def test_running_execution_requires_cooperative_cancellation(state, immediate):
    port = MemoryPort()
    port.row["state"] = state
    ControlService(port).cancel(
        Principal("alice"), port.tenant, port.row["id"], CancelCase(expected_version=2)
    )
    assert port.writes == [(port.row["id"], 2, immediate)]


def test_attempt_queue_checks_state_version_grant_and_stop_before_port_write():
    port = MemoryPort()
    port.row["state"] = "READY_TO_REPAIR"
    service = ControlService(port)
    request = AttemptRequest(expected_version=2, estimate_microusd=500)
    assert (
        service.queue_attempt(Principal("alice"), port.tenant, port.row["id"], request)["attempt"]
        == 1
    )
    assert port.writes == [(port.row["id"], 2, 500)]
    port.writes.clear()
    port.row["cancel_requested"] = True
    with pytest.raises(Conflict):
        service.queue_attempt(Principal("alice"), port.tenant, port.row["id"], request)
    port.row["cancel_requested"] = False
    port.granted = False
    with pytest.raises(AccessDenied):
        service.queue_attempt(Principal("alice"), port.tenant, port.row["id"], request)
    port.granted = True
    with pytest.raises(Conflict, match="Emergency stop"):
        ControlService(port, emergency_stop=True).queue_attempt(
            Principal("alice"), port.tenant, port.row["id"], request
        )
    assert not port.writes


def test_attempt_estimate_fits_database_bigint():
    with pytest.raises(ValidationError):
        AttemptRequest(expected_version=1, estimate_microusd=9_223_372_036_854_775_808)

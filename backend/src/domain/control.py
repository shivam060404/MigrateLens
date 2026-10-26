"""Tenant authorization and lifecycle policy, independent of transport and storage."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class AccessDenied(ValueError):
    pass


class Conflict(ValueError):
    pass


class NotFound(ValueError):
    pass


class BudgetExceeded(ValueError):
    pass


class ControlUnavailable(RuntimeError):
    pass


class Role(StrEnum):
    OWNER = "owner"
    MAINTAINER = "maintainer"
    REVIEWER = "reviewer"
    VIEWER = "viewer"
    WORKER = "worker"


@dataclass(frozen=True)
class Principal:
    subject: str

    def __post_init__(self):
        if not self.subject or len(self.subject) > 128:
            raise AccessDenied("Invalid authenticated subject")


@dataclass(frozen=True)
class Membership:
    tenant_id: UUID
    subject: str
    role: Role


def authorize(membership: Membership, repository_granted: bool, action: str) -> None:
    permissions = {
        "read": set(Role),
        "create": {Role.OWNER, Role.MAINTAINER},
        "cancel": {Role.OWNER, Role.MAINTAINER},
        "execute": {Role.WORKER},
    }
    if not repository_granted or membership.role not in permissions.get(action, set()):
        raise AccessDenied("Repository action is not authorized")


TRANSITIONS: dict[str, frozenset[str]] = {
    "RECEIVED": frozenset({"ANALYZING", "CANCELLED"}),
    "ANALYZING": frozenset({"WAITING_FOR_INPUT", "READY_TO_REPAIR", "COMPLETED", "FAILED"}),
    "WAITING_FOR_INPUT": frozenset({"ANALYZING", "CANCELLED"}),
    "READY_TO_REPAIR": frozenset({"REPAIRING", "CANCELLED"}),
    "REPAIRING": frozenset({"VALIDATING", "WAITING_FOR_INPUT", "FAILED", "CANCELLED"}),
    "VALIDATING": frozenset({"REPAIRING", "AWAITING_REVIEW", "COMPLETED", "FAILED", "CANCELLED"}),
    "AWAITING_REVIEW": frozenset({"PUBLISHING", "ANALYZING", "COMPLETED", "CANCELLED"}),
    "PUBLISHING": frozenset({"PUBLISHED", "AWAITING_REVIEW", "FAILED"}),
    "PUBLISHED": frozenset(),
    "COMPLETED": frozenset(),
    "FAILED": frozenset(),
    "CANCELLED": frozenset(),
}


def transition(current: str, target: str, *, revision_changed: bool = False) -> None:
    if target not in TRANSITIONS.get(current, frozenset()):
        raise Conflict("Illegal lifecycle transition")
    if (
        current in {"WAITING_FOR_INPUT", "AWAITING_REVIEW"}
        and target == "ANALYZING"
        and not revision_changed
    ):
        raise Conflict("Reanalysis requires a new evidence revision")


def reserve_budget(limit: int, spent: int, reserved: int, estimate: int, attempts: int) -> None:
    if min(limit, spent, reserved, estimate, attempts) < 0 or estimate == 0:
        raise ValueError("Budget values must be nonnegative and reservation positive")
    if attempts >= 3 or spent + reserved + estimate > limit:
        raise BudgetExceeded("Attempt or tenant budget exhausted")

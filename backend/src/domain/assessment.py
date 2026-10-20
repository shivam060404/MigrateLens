"""Acceptance is deterministic and independent of generators and transports."""

from src.domain.models import Check, Outcome


def verdict(checks: list[Check], required: tuple[str, ...]):
    if not required or len(set(required)) != len(required):
        raise ValueError("Acceptance plan must name unique required checks")
    if len({c.id for c in checks}) != len(checks):
        return "VALIDATION_FAILED"
    by_id = {c.id: c.outcome for c in checks}
    if any(by_id.get(k) in {Outcome.FAIL, Outcome.ERROR, Outcome.FLAKY} for k in required):
        return "VALIDATION_FAILED"
    if any(by_id.get(k) != Outcome.PASS for k in required):
        return "PATCH_PREPARED"
    return "VERIFIED_FOR_DECLARED_SCOPE"

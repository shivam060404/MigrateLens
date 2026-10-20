"""Validate report structure and internal consistency, never claim signed provenance."""

from src.domain.assessment import verdict
from src.domain.models import MigrationPlan, ValidationEvidence, digest


def validate_manifest(data: object) -> ValidationEvidence:
    evidence = ValidationEvidence.model_validate(data)
    payload = evidence.model_dump(mode="json", exclude={"fingerprint"})
    if digest(payload) != evidence.fingerprint:
        raise ValueError("Evidence fingerprint mismatch")
    if evidence.verdict == "VERIFIED_FOR_DECLARED_SCOPE":
        required = MigrationPlan.model_fields["required_checks"].default
        if verdict(list(evidence.checks), required) != evidence.verdict:
            raise ValueError("Declared verdict is unsupported by its check matrix")
        identities = {
            "source",
            "candidate",
            "patch",
            "mapping",
            "plan",
            "policy",
            "test_suite",
            "old_contract",
            "new_contract",
            "provider_old",
            "provider_new",
        }
        if not identities.issubset(evidence.identities):
            raise ValueError("Verified evidence is missing required identities")
    return evidence

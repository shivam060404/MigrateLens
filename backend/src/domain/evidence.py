"""Validate report structure and internal consistency, never claim signed provenance."""

import re

from src.domain.assessment import verdict
from src.domain.models import MigrationPlan, ValidationEvidence, digest


def validate_manifest(data: object) -> ValidationEvidence:
    evidence = ValidationEvidence.model_validate(data)
    payload = evidence.model_dump(mode="json", exclude={"fingerprint"})
    if digest(payload) != evidence.fingerprint:
        raise ValueError("Evidence fingerprint mismatch")
    if evidence.schema_version == "2":
        required = {
            "source",
            "policy",
            "mapping",
            "old_contract",
            "new_contract",
            "patch",
            "dossier",
            "implementation",
            "runner_implementation",
        }
        if not required.issubset(evidence.identities):
            raise ValueError("Version 2 evidence is missing required identities")
        if any(not re.fullmatch(r"[a-f0-9]{64}", evidence.identities[key]) for key in required):
            raise ValueError("Version 2 content identities must be SHA256 digests")
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
        if evidence.schema_version == "2" and not re.fullmatch(
            r"[a-f0-9]{64}", evidence.identities.get("proposal", "")
        ):
            raise ValueError("Verified evidence requires a pinned patch proposal")
    return evidence

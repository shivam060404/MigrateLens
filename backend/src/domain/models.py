"""Canonical contracts. Generate JSON schemas from these strict models."""

import hashlib
import json
from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode()


def digest(value: object) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else canonical(value)).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Outcome(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    UNAVAILABLE = "UNAVAILABLE"
    SKIPPED = "SKIPPED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    FLAKY = "FLAKY"


class Policy(Strict):
    schema_version: Literal["1"] = "1"
    allowed_path: Literal["src/integrations/customer/client.ts"] = (
        "src/integrations/customer/client.ts"
    )
    max_attempts: int = Field(default=3, ge=1, le=3)
    max_changed_files: int = Field(default=1, ge=1, le=8)
    max_changed_lines: int = Field(default=50, ge=1, le=300)
    max_run_seconds: int = Field(default=120, ge=1, le=1800)
    max_model_calls: int = Field(default=0, ge=0, le=8)
    publication: Literal["preview", "draft_after_authorized_review"] = "preview"


class MigrationPlan(Strict):
    schema_version: Literal["1"] = "1"
    scenario: str = Field(max_length=80)
    rule: Literal["ML-PATH-001", "ML-FIELD-001", "ML-QUERY-001"]
    mapping_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    required_checks: tuple[str, ...] = (
        "BASELINE_OLD",
        "REPRO_NEW",
        "REPAIR_NEW",
        "REGRESSION",
        "STATIC",
        "POLICY",
    )
    invariants: tuple[str, ...] = (
        "identity",
        "meaning",
        "null",
        "missing",
        "not_found",
        "error",
        "encoding",
        "unrelated_fields",
    )
    overlap_reason: str = "Old-version overlap is not required by the frozen fixture profile."


class PatchProposal(Strict):
    schema_version: Literal["1"] = "1"
    status: Literal["PROPOSED", "NEEDS_CLARIFICATION", "UNSUPPORTED"]
    path: str = Field(max_length=200)
    source_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    candidate_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    evidence_refs: tuple[str, ...] = Field(max_length=20)
    rationale: str = Field(max_length=2000)


class Check(Strict):
    id: str = Field(max_length=80)
    outcome: Outcome
    reason: str = Field(max_length=2000)
    observations: dict = Field(default_factory=dict)
    duration_ms: int = Field(default=0, ge=0)


class ValidationEvidence(Strict):
    schema_version: Literal["1"] = "1"
    tenant: str = Field(default="fictional-demo", pattern=r"^[a-z0-9][a-z0-9-]{0,79}$")
    repository: str = Field(default="northstar-consumer", pattern=r"^[a-z0-9][a-z0-9-]{0,79}$")
    scenario: str
    revision: int = 1
    created_at: str
    verdict: Literal[
        "ANALYSIS_ONLY",
        "PATCH_PREPARED",
        "LOCAL_CHECKS_PASSED",
        "VERIFIED_FOR_DECLARED_SCOPE",
        "NEEDS_CLARIFICATION",
        "UNSUPPORTED",
        "VALIDATION_FAILED",
    ]
    provider_kind: Literal["fixture"] = "fixture"
    identities: dict[str, str]
    checks: tuple[Check, ...]
    limitations: tuple[str, ...]
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    publication: Literal["PR preview", "none"] = "PR preview"


class PublicationRequest(Strict):
    schema_version: Literal["1"] = "1"
    case_id: str = Field(max_length=80)
    expected_revision: int = Field(ge=1)
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    base_sha: str = Field(pattern=r"^[a-f0-9]{40}$")
    candidate_sha: str = Field(pattern=r"^[a-f0-9]{40}$")
    approval_id: str = Field(max_length=80)

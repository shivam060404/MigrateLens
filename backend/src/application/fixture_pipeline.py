"""Fixture change-to-evidence use case. No filesystem, subprocess or framework imports."""

import difflib
from dataclasses import dataclass

from src.application.ports import (
    Analyzer,
    ContractDetector,
    EvidenceStore,
    FixtureInputs,
    Verifier,
)
from src.domain.assessment import verdict
from src.domain.models import (
    Check,
    MigrationPlan,
    Outcome,
    PatchProposal,
    Policy,
    ValidationEvidence,
    digest,
    now,
)
from src.domain.patch_policy import check_patch

SCENARIOS = (
    "path",
    "field",
    "query",
    "ambiguous",
    "amount-unit",
    "pagination",
    "required-field",
    "unchanged",
    "dynamic",
)
SUPPORTED = {"path", "field", "query"}
LIMITATIONS = (
    "Synthetic Northstar fixture only; not customer or production evidence.",
    "Host subprocess adapter is not a sandbox; customer code execution is disabled.",
    "Source and candidate content hashes identify uncommitted local fixture inputs.",
    "Local export is unsigned; pilot signing and isolated runner identity are unavailable.",
    "Structural fixture detector only; pinned oasdiff integration is not yet verified.",
)
ABSTENTIONS = {
    "ambiguous": (
        "NEEDS_CLARIFICATION",
        "Legal name and nickname lack approved semantic equivalence.",
    ),
    "required-field": (
        "NEEDS_CLARIFICATION",
        "No approved value for the required field; no default invented.",
    ),
    "amount-unit": ("UNSUPPORTED", "Unit conversion is outside supported repairs."),
    "pagination": ("UNSUPPORTED", "Changed pagination semantics require a behavior decision."),
    "dynamic": ("UNSUPPORTED", "Dynamic URL cannot be resolved within registered static scope."),
    "unchanged": ("ANALYSIS_ONLY", "Documentation-only fixture produces no contract findings."),
}


@dataclass
class FixturePipeline:
    inputs: FixtureInputs
    analyzer: Analyzer
    verifier: Verifier
    detector: ContractDetector
    store: EvidenceStore | None = None
    emergency_stop: bool = False

    def run(self, scenario: str) -> ValidationEvidence:
        if self.emergency_stop:
            raise RuntimeError("Emergency stop active")
        if scenario not in SCENARIOS:
            raise ValueError("Only registered fictional scenarios may execute")
        base = self.inputs.source
        policy = Policy()
        identities = {
            **self.inputs.identities,
            "source": digest(base.encode()),
            "policy": digest(policy.model_dump()),
            "mapping": digest(self.inputs.mappings),
            "old_contract": digest(self.inputs.old_contract),
            "new_contract": digest(self.inputs.new_contract),
        }
        checks: list[Check] = []
        patch = ""
        dossier: dict[str, object] = {
            "classification": "Fictional demo data",
            "scenario": scenario,
            "scope": "registered Northstar integration only",
        }
        if scenario not in SUPPORTED:
            result, reason = ABSTENTIONS[scenario]
            dossier["reason"] = reason
            dossier["assessment_mode"] = (
                "Registered exclusion fixture; no consumer impact or runtime breakage claimed."
            )
            dossier["diff"] = self.detector.detect(
                self.inputs.old_contract, self.inputs.new_contract
            )
        else:
            mapping = self.inputs.mappings["mappings"][scenario]
            plan = MigrationPlan(
                scenario=scenario, rule=mapping["rule"], mapping_hash=digest(self.inputs.mappings)
            )
            # Freeze every acceptance identity before invoking the repair generator.
            identities.update(
                {
                    "mapping": digest(self.inputs.mappings),
                    "plan": digest(plan.model_dump()),
                    "old_contract": digest(self.inputs.old_contract),
                    "new_contract": digest(self.inputs.new_contract),
                    "provider_old": f"northstar-{scenario}-old-1",
                    "provider_new": f"northstar-{scenario}-new-1",
                }
            )
            dossier.update(
                {
                    "diff": self.detector.detect(
                        self.inputs.old_contract, self.inputs.new_contract
                    ),
                    "plan": plan.model_dump(),
                    "policy": policy.model_dump(),
                    "mapping": mapping,
                    "usage": self.analyzer.analyze(base, scenario),
                }
            )
            checks.append(self.verifier.behavior(base, scenario, "old", "BASELINE_OLD"))
            checks.append(
                self.verifier.behavior(base, scenario, "new", "REPRO_NEW", reproduce=True)
            )
            if any(c.outcome != Outcome.PASS for c in checks):
                result = (
                    "VALIDATION_FAILED"
                    if any(
                        c.outcome in {Outcome.FAIL, Outcome.ERROR, Outcome.FLAKY} for c in checks
                    )
                    else "ANALYSIS_ONLY"
                )
                dossier["reason"] = (
                    "Baseline or reproduction incomplete; no repair attempt launched."
                )
            else:
                candidate = self.analyzer.analyze(base, scenario, repair=True)["source"]
                patch = "".join(
                    difflib.unified_diff(
                        base.splitlines(keepends=True),
                        candidate.splitlines(keepends=True),
                        fromfile="a/" + policy.allowed_path,
                        tofile="b/" + policy.allowed_path,
                    )
                )
                identities.update(
                    {"candidate": digest(candidate.encode()), "patch": digest(patch.encode())}
                )
                proposal = PatchProposal(
                    status="PROPOSED",
                    path=policy.allowed_path,
                    source_hash=identities["source"],
                    candidate_hash=identities["candidate"],
                    evidence_refs=(identities["mapping"], identities["plan"]),
                    rationale="Deterministic recipe for the explicitly approved fictional mapping.",
                )
                dossier["proposal"] = proposal.model_dump(mode="json")
                identities["proposal"] = digest(dossier["proposal"])
                checks.append(check_patch(base, candidate, policy.allowed_path, policy))
                if checks[-1].outcome == Outcome.PASS:
                    checks.append(self.verifier.behavior(candidate, scenario, "new", "REPAIR_NEW"))
                    checks.append(self.verifier.behavior(candidate, scenario, "new", "REGRESSION"))
                    checks.append(self.verifier.static_check(candidate))
                checks.append(
                    Check(
                        id="OVERLAP_OLD", outcome=Outcome.NOT_APPLICABLE, reason=plan.overlap_reason
                    )
                )
                result = verdict(checks, plan.required_checks)
        identities["patch"] = digest(patch.encode())
        identities["dossier"] = digest(dossier)
        metadata = {
            "schema_version": "2",
            "tenant": "fictional-demo",
            "repository": "northstar-consumer",
            "scenario": scenario,
            "revision": 1,
            "created_at": now(),
            "verdict": result,
            "provider_kind": "fixture",
            "identities": identities,
            "checks": [c.model_dump(mode="json") for c in checks],
            "limitations": LIMITATIONS,
            "publication": "PR preview" if patch else "none",
        }
        evidence = ValidationEvidence.model_validate({**metadata, "fingerprint": digest(metadata)})
        if self.store:
            self.store.export(evidence, dossier, patch)
        return evidence

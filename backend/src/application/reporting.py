"""Render local evidence without inventing facts or interpreting model output."""

import json
from src.domain.evidence import validate_manifest
from src.domain.models import ValidationEvidence, digest


def render_bundle(evidence: ValidationEvidence, dossier: dict, patch: str) -> dict[str, bytes]:
    validate_manifest(evidence.model_dump(mode="json"))
    if evidence.schema_version != "2":
        raise ValueError("Historical version 1 evidence is read-only; rerun before exporting")
    if evidence.identities.get("patch") != digest(patch.encode()):
        raise ValueError("Export patch does not match tested patch identity")
    if evidence.identities.get("dossier") != digest(dossier):
        raise ValueError("Export dossier does not match frozen dossier identity")
    if evidence.publication != ("PR preview" if patch else "none"):
        raise ValueError("Publication preview does not match patch availability")
    rows = "\n".join(
        f"| {check.id} | {check.outcome} | {check.reason} |" for check in evidence.checks
    )
    report = (
        f"# Fictional migration report: {evidence.scenario}\n\nVerdict: **{evidence.verdict}**\n\n"
        f"Fingerprint: `{evidence.fingerprint}`\n\n"
        "Provenance: unsigned local export. Not authenticated customer evidence.\n\n"
        f"| Check | Outcome | Evidence scope |\n|---|---|---|\n{rows}\n\n"
        + "\n".join(f"- {limit}" for limit in evidence.limitations)
        + "\n"
    )
    files = {
        "manifest.json": (json.dumps(evidence.model_dump(mode="json"), indent=2) + "\n").encode(),
        "dossier.json": (json.dumps(dossier, indent=2) + "\n").encode(),
        "repair.patch": patch.encode(),
        "report.md": report.encode(),
        "pr-preview.md": (
            "# PR preview — not published\n\n"
            + report
            + "\nReview and deployment remain customer-owned. No publication authorization exists.\n"
        ).encode(),
    }
    files["checksums.json"] = (
        json.dumps(
            {"schema_version": "1", "files": {name: digest(data) for name, data in files.items()}},
            indent=2,
        )
        + "\n"
    ).encode()
    return files

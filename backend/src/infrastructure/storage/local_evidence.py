"""Private local fixture export; no object-store or multi-tenant security claim."""

from pathlib import Path

from src.application.reporting import render_bundle
from src.domain.execution_policy import ExecutionDenied
from src.domain.models import ValidationEvidence
from src.infrastructure.security.fixture_admission import assert_no_symlinks


def export(root: Path, evidence: ValidationEvidence, dossier: dict, patch: str) -> Path:
    # Revalidate even if an internal caller used Pydantic model_construct/model_copy.
    evidence = ValidationEvidence.model_validate(evidence.model_dump(mode="json"))
    if evidence.tenant != "fictional-demo" or evidence.repository != "northstar-consumer":
        raise ExecutionDenied("Local export only supports the registered fictional namespace")
    files = render_bundle(evidence, dossier, patch)
    target = root / evidence.tenant / evidence.fingerprint
    assert_no_symlinks(target.absolute())
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    target.mkdir(exist_ok=False, mode=0o700)
    for name, payload in files.items():
        with (target / name).open("xb") as file:
            file.write(payload)
    return target


class LocalEvidenceStore:
    def __init__(self, root: Path):
        self.root = root

    def export(self, evidence: ValidationEvidence, dossier: dict, patch: str) -> None:
        export(self.root, evidence, dossier, patch)

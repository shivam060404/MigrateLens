"""Strict acceptance gates. Binding failures are failures, never replaced with mocks."""

import json
from urllib.request import urlopen

import pytest
from src.bootstrap import run_fixture
from src.domain.models import Outcome, PatchProposal, digest
from src.domain.evidence import validate_manifest
from src.infrastructure.fixtures.provider import provider


@pytest.mark.parametrize("scenario", ["path", "field", "query"])
def test_real_provider_reproduction_and_repair(scenario, tmp_path, monkeypatch):
    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GITHUB_TOKEN", "GH_TOKEN"]:
        monkeypatch.delenv(key, raising=False)
    evidence = run_fixture(scenario, tmp_path)
    assert evidence.verdict == "VERIFIED_FOR_DECLARED_SCOPE", evidence.model_dump()
    assert evidence.schema_version == "2"
    folder = tmp_path / evidence.tenant / evidence.fingerprint
    manifest = json.loads((folder / "manifest.json").read_text())
    validate_manifest(manifest)
    dossier = json.loads((folder / "dossier.json").read_text())
    proposal = PatchProposal.model_validate(dossier["proposal"])
    assert proposal.source_hash == evidence.identities["source"]
    assert proposal.candidate_hash == evidence.identities["candidate"]
    assert evidence.identities["dossier"] == digest(dossier)
    assert evidence.identities["patch"] == digest((folder / "repair.patch").read_bytes())
    assert "not published" in (folder / "pr-preview.md").read_text()


def test_wrong_candidate_is_rejected_by_behavior_not_just_typecheck(tmp_path):
    evidence = run_fixture("path", tmp_path, wrong_patch=True)
    assert evidence.verdict == "VALIDATION_FAILED", evidence.model_dump()
    checks = {check.id: check.outcome for check in evidence.checks}
    assert checks["STATIC"] == Outcome.PASS
    assert checks["REPAIR_NEW"] == Outcome.FAIL


def test_provider_sessions_reset():
    for _ in range(2):
        with provider("path", "old") as (url, interactions):
            assert interactions == []
            with urlopen(url + "/v1/customers/ada", timeout=3) as response:
                assert json.load(response)["name"] == "Ada Lovelace"
            assert len(interactions) == 1

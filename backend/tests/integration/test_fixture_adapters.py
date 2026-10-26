"""Real Node adapter checks; these are not live provider verification."""

import json

import pytest

from src.bootstrap import run_fixture
from src.config.paths import SOURCE
from src.domain.models import Outcome, digest
from src.infrastructure.analysis.typescript import TypeScriptFixtureAnalyzer
from src.infrastructure.verification.fixture_verifier import static_check


@pytest.mark.parametrize(
    "scenario,expected",
    [
        ("path", "/v2/customers/"),
        ("field", "customer.profile?.displayName"),
        ("query", 'query.set("limit"'),
    ],
)
def test_recipes_transform_registered_nodes_and_typecheck(scenario, expected):
    result = TypeScriptFixtureAnalyzer().analyze(SOURCE.read_text(), scenario, repair=True)
    assert expected in result["source"]
    assert "customer.unrelated.name" in result["source"]
    assert static_check(result["source"]).outcome == Outcome.PASS
    assert "/v1/customers/" in SOURCE.read_text(), "Original fixture must remain unchanged"


def test_ambiguous_mapping_exports_no_patch_and_valid_fingerprint(tmp_path):
    evidence = run_fixture("ambiguous", tmp_path)
    assert evidence.verdict == "NEEDS_CLARIFICATION"
    folder = tmp_path / evidence.tenant / evidence.fingerprint
    assert (folder / "repair.patch").read_text() == ""
    manifest = json.loads((folder / "manifest.json").read_text())
    fingerprint = manifest.pop("fingerprint")
    assert digest(manifest) == fingerprint


@pytest.mark.parametrize(
    "scenario,expected",
    [
        ("amount-unit", "UNSUPPORTED"),
        ("pagination", "UNSUPPORTED"),
        ("required-field", "NEEDS_CLARIFICATION"),
        ("unchanged", "ANALYSIS_ONLY"),
        ("dynamic", "UNSUPPORTED"),
    ],
)
def test_registered_abstentions_are_versioned_and_export_no_patch(tmp_path, scenario, expected):
    evidence = run_fixture(scenario, tmp_path)
    assert evidence.verdict == expected
    assert evidence.schema_version == "2"
    folder = tmp_path / evidence.tenant / evidence.fingerprint
    assert (folder / "repair.patch").read_bytes() == b""
    assert evidence.identities["dossier"] == digest(
        json.loads((folder / "dossier.json").read_text())
    )
    assert evidence.publication == "none"
    dossier = json.loads((folder / "dossier.json").read_text())
    if scenario in {"amount-unit", "pagination", "required-field"}:
        assert dossier["diff"]["findings"], "Exclusion must have a concrete contract fixture"
    elif scenario == "unchanged":
        assert dossier["diff"]["findings"] == []

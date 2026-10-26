"""Evidence/command policy tests; these do not constitute HTTP verification."""

import json
from types import SimpleNamespace

import pytest

from src.application.commands import FixtureCommands
from src.application.fixture_pipeline import ABSTENTIONS
from src.application.reporting import render_bundle
from src.bootstrap import implementation_fingerprint, run_fixture
from src.domain.evidence import validate_manifest
from src.domain.models import ValidationEvidence, digest
from src.domain.execution_policy import ExecutionDenied
from src.infrastructure.fixtures.provider import provider
from src.infrastructure.security.fixture_admission import authorize_source, read_reviewed


def rebind(evidence, **updates):
    data = evidence.model_dump(mode="json", exclude={"fingerprint"})
    data.update(updates)
    return ValidationEvidence.model_validate({**data, "fingerprint": digest(data)})


@pytest.fixture
def exported(tmp_path):
    evidence = run_fixture("ambiguous", tmp_path)
    folder = tmp_path / evidence.tenant / evidence.fingerprint
    return evidence, json.loads((folder / "dossier.json").read_text())


def test_changed_dossier_rejected(exported):
    evidence, dossier = exported
    with pytest.raises(ValueError, match="dossier"):
        render_bundle(evidence, {**dossier, "reason": "invented approval"}, "")


def test_empty_patch_cannot_replace_recorded_nonempty_patch(exported):
    evidence, dossier = exported
    evidence = rebind(
        evidence,
        identities={**evidence.identities, "patch": digest(b"original patch")},
        publication="PR preview",
    )
    with pytest.raises(ValueError, match="patch identity"):
        render_bundle(evidence, dossier, "")


def test_abstention_binds_contracts_dossier_and_empty_patch(exported):
    evidence, dossier = exported
    assert evidence.schema_version == "2"
    assert evidence.identities["patch"] == digest(b"")
    assert evidence.identities["dossier"] == digest(dossier)
    assert {
        "mapping",
        "old_contract",
        "new_contract",
        "implementation",
    } <= evidence.identities.keys()
    validate_manifest(evidence.model_dump(mode="json"))


def test_invalid_v2_identity_rejected_even_with_consistent_fingerprint(exported):
    evidence, _ = exported
    evidence = rebind(evidence, identities={**evidence.identities, "dossier": "not-a-hash"})
    with pytest.raises(ValueError, match="SHA256"):
        validate_manifest(evidence.model_dump(mode="json"))


def test_historical_v1_remains_readable_but_cannot_be_reexported(exported):
    evidence, dossier = exported
    old = rebind(evidence, schema_version="1")
    assert validate_manifest(old.model_dump(mode="json")).schema_version == "1"
    with pytest.raises(ValueError, match="read-only"):
        render_bundle(old, dossier, "")


@pytest.mark.parametrize("scenario", list(ABSTENTIONS))
def test_demo_fails_when_abstention_is_incorrect(scenario):
    def factory(name, _negative):
        expected = ABSTENTIONS[name][0] if name in ABSTENTIONS else "VERIFIED_FOR_DECLARED_SCOPE"
        evidence = SimpleNamespace(
            scenario=name,
            verdict="VERIFIED_FOR_DECLARED_SCOPE" if name == scenario else expected,
            fingerprint="a" * 64,
        )
        return SimpleNamespace(run=lambda _: evidence)

    assert FixtureCommands(factory).execute("demo").exit_code == 1


def test_dynamic_exclusion_is_not_executable():
    source = read_reviewed("fixtures/consumers/unsupported/dynamic.ts").decode()
    assert "pathFromCaller" in source
    with pytest.raises(ExecutionDenied):
        authorize_source(source)


@pytest.mark.parametrize("scenario,version", [("unknown", "old"), ("path", "latest")])
def test_unknown_provider_profile_fails_before_binding(scenario, version):
    with pytest.raises(ValueError, match="registered"):
        with provider(scenario, version):
            pytest.fail("Unregistered provider started")


@pytest.mark.parametrize(
    "changed",
    [
        "backend/src/infrastructure/execution/process.py",
        "backend/src/domain/patch_policy.py",
        "pnpm-lock.yaml",
    ],
)
def test_implementation_identity_changes_with_execution_policy_or_dependencies(tmp_path, changed):
    paths = [
        "backend/analyzer-ts/tsconfig.json",
        "backend/analyzer-ts/package.json",
        "backend/pyproject.toml",
        "backend/requirements.lock",
        "pnpm-lock.yaml",
        changed,
    ]
    for name in paths:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("original test input")
    before = implementation_fingerprint(tmp_path)
    (tmp_path / changed).write_text("changed test input")
    assert implementation_fingerprint(tmp_path) != before


def test_proposal_and_export_wiring_with_explicit_unit_doubles():
    """Exercise successful orchestration wiring; never substitute for real-provider E2E."""
    from src.application.fixture_pipeline import FixturePipeline
    from src.application.ports import FixtureInputs
    from src.domain.models import Check, Outcome

    class AnalyzerDouble:
        def analyze(self, source, scenario, repair=False):
            return {"source": "const value = 2;\n"} if repair else {"usages": []}

    class VerifierDouble:
        def behavior(self, source, scenario, version, check_id, reproduce=False):
            return Check(id=check_id, outcome=Outcome.PASS, reason="Explicit unit double")

        def static_check(self, source):
            return Check(id="STATIC", outcome=Outcome.PASS, reason="Explicit unit double")

    captured = {}

    class StoreDouble:
        def export(self, evidence, dossier, patch):
            captured.update(render_bundle(evidence, dossier, patch))

    inputs = FixtureInputs(
        source="const value = 1;\n",
        mappings={"mappings": {"path": {"rule": "ML-PATH-001"}}},
        old_contract={"unit_double": "old"},
        new_contract={"unit_double": "new"},
        identities={
            key: "a" * 64 for key in ["implementation", "runner_implementation", "test_suite"]
        },
    )
    pipeline = FixturePipeline(
        inputs=inputs,
        analyzer=AnalyzerDouble(),
        verifier=VerifierDouble(),
        detector=SimpleNamespace(detect=lambda *_: {"findings": ["unit double"]}),
        store=StoreDouble(),
    )
    evidence = pipeline.run("path")
    dossier = json.loads(captured["dossier.json"])
    assert evidence.identities["proposal"] == digest(dossier["proposal"])
    assert dossier["proposal"]["candidate_hash"] == evidence.identities["candidate"]
    for name, expected in json.loads(captured["checksums.json"])["files"].items():
        assert digest(captured[name]) == expected

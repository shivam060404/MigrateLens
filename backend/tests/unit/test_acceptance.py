import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.api.app import create_app
from src.config.settings import Settings
from src.domain.assessment import verdict
from src.domain.models import Check, Outcome, PatchProposal, Policy
from src.domain.patch_policy import check_patch, validate_path
from src.infrastructure.contracts.openapi import detect, fixture_contract, parse_contract


@pytest.mark.parametrize("outcome", [Outcome.FAIL, Outcome.ERROR, Outcome.FLAKY])
def test_failed_or_inconsistent_required_checks_never_validate(outcome):
    assert (
        verdict([Check(id="REPAIR_NEW", outcome=outcome, reason="Observed")], ("REPAIR_NEW",))
        == "VALIDATION_FAILED"
    )


@pytest.mark.parametrize("outcome", [Outcome.UNAVAILABLE, Outcome.SKIPPED, Outcome.NOT_APPLICABLE])
def test_missing_required_evidence_never_validates(outcome):
    assert (
        verdict([Check(id="REPAIR_NEW", outcome=outcome, reason="Missing")], ("REPAIR_NEW",))
        == "PATCH_PREPARED"
    )


def test_missing_check_does_not_validate():
    assert verdict([], ("REPAIR_NEW",)) == "PATCH_PREPARED"


@pytest.mark.parametrize(
    "path", ["../client.ts", "/client.ts", "src/../client.ts", "src\\client.ts", "./src/client.ts"]
)
def test_unsafe_paths_are_rejected(path):
    with pytest.raises(ValueError):
        validate_path(path)


def test_protected_tests_cannot_be_changed():
    assert (
        check_patch("assert(x)", "test.skip(x)", "tests/test.ts", Policy()).outcome == Outcome.FAIL
    )


def test_production_and_extra_schema_fields_rejected():
    with pytest.raises(ValidationError):
        Settings(environment="production")
    with pytest.raises(ValidationError):
        PatchProposal(
            status="PROPOSED",
            path="src/x.ts",
            source_hash="a" * 64,
            candidate_hash="b" * 64,
            evidence_refs=(),
            rationale="fixture",
            safe=True,
        )


def test_documentation_change_is_not_repair_evidence():
    old = fixture_contract("path", "old")
    new = fixture_contract("path", "old")
    new["info"]["description"] = "Only docs"
    assert detect(old, new)["findings"] == []


def test_unapproved_refs_are_rejected():
    with pytest.raises(ValueError, match="References"):
        parse_contract(
            b'{"openapi":"3.1.0","paths":{},"schema":{"$ref":"http://169.254.169.254/"}}'
        )


def test_health_does_not_claim_readiness():
    with TestClient(create_app(Settings(environment="test"))) as client:
        assert client.get("/api/v1/health/live").status_code == 200
        assert client.get("/api/v1/health/ready").status_code == 503
        assert (
            client.get("/api/v1/health/live", headers={"host": "untrusted.example"}).status_code
            == 400
        )


@pytest.mark.parametrize("settings", [{"auth_mode": "oidc"}, {"runner_mode": "pilot"}])
def test_unimplemented_integrations_cannot_silently_use_fixture_adapters(settings):
    with pytest.raises(ValidationError, match="Only explicitly labeled"):
        Settings(**settings)

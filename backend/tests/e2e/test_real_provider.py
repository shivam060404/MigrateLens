"""Strict acceptance gates. Binding failures are failures, never replaced with mocks."""

import pytest
from src.bootstrap import run_fixture
from src.domain.models import Outcome


@pytest.mark.parametrize("scenario", ["path", "field", "query"])
def test_real_provider_reproduction_and_repair(scenario, tmp_path):
    evidence = run_fixture(scenario, tmp_path)
    assert evidence.verdict == "VERIFIED_FOR_DECLARED_SCOPE", evidence.model_dump()


def test_wrong_candidate_is_rejected_by_behavior_not_just_typecheck(tmp_path):
    evidence = run_fixture("path", tmp_path, wrong_patch=True)
    assert evidence.verdict == "VALIDATION_FAILED", evidence.model_dump()
    checks = {check.id: check.outcome for check in evidence.checks}
    assert checks["STATIC"] == Outcome.PASS
    assert checks["REPAIR_NEW"] == Outcome.FAIL

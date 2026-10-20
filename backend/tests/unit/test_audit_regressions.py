import json

import pytest

from src.application.commands import FixtureCommands
from src.cli.main import main
from src.domain.assessment import verdict
from src.domain.evidence import validate_manifest
from src.domain.fixture_acceptance import assess_behavior, expected
from src.domain.models import Check, Outcome, digest


def test_later_pass_cannot_overwrite_failed_check():
    checks = [
        Check(id="STATIC", outcome=Outcome.FAIL, reason="failed"),
        Check(id="STATIC", outcome=Outcome.PASS, reason="later passed"),
    ]
    assert verdict(checks, ("STATIC",)) == "VALIDATION_FAILED"


@pytest.mark.parametrize("required", [(), ("STATIC", "STATIC")])
def test_empty_or_duplicate_plan_is_invalid(required):
    with pytest.raises(ValueError, match="unique required"):
        verdict([], required)


def test_forged_test_results_without_provider_calls_do_not_pass():
    result = assess_behavior(expected(), [], "path", "new", "REPAIR_NEW")
    assert result.outcome == Outcome.FAIL
    assert (
        assess_behavior({"all_passed": True}, [], "path", "new", "REPAIR_NEW").outcome
        == Outcome.ERROR
    )


def test_reproduction_requires_registered_requests_not_arbitrary_failures():
    result = assess_behavior(
        [{"error": "anything"}] * 10,
        [{"method": "POST", "path": "/other"}] * 10,
        "path",
        "new",
        "REPRO_NEW",
        reproduce=True,
    )
    assert result.outcome == Outcome.FAIL


def test_self_consistent_hash_cannot_upgrade_empty_check_matrix():
    data = {
        "schema_version": "1",
        "tenant": "fictional-demo",
        "repository": "northstar-consumer",
        "scenario": "path",
        "revision": 1,
        "created_at": "2026-10-20T00:00:00Z",
        "verdict": "VERIFIED_FOR_DECLARED_SCOPE",
        "provider_kind": "fixture",
        "identities": {},
        "checks": [],
        "limitations": [],
        "publication": "none",
    }
    with pytest.raises(ValueError, match="unsupported"):
        validate_manifest({**data, "fingerprint": digest(data)})


def test_cli_delegates_business_command_and_preserves_failure(monkeypatch, capsys):
    from src.application.commands import CommandResponse

    seen = []

    class Commands:
        def execute(self, command, scenario, manifest):
            seen.append((command, scenario, manifest))
            return CommandResponse({"status": "incomplete"}, 1)

    monkeypatch.setattr("src.cli.main.create_commands", lambda output: Commands())
    assert main(["repair", "--scenario", "field"]) == 1
    assert seen == [("repair", "field", None)]
    assert json.loads(capsys.readouterr().out) == {"status": "incomplete"}


def test_unsupported_scan_does_not_launch_adapter():
    def factory(*_):
        pytest.fail("Unsupported scan reached an adapter")

    with pytest.raises(ValueError, match="registered"):
        FixtureCommands(factory).execute("scan", "ambiguous")

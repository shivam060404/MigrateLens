"""Trusted external fixture assertions. Never trust candidate-reported test verdicts."""

import json
from src.domain.models import Check, Outcome
from src.domain.fixture_acceptance import OPERATIONS, assess_behavior
from src.infrastructure.fixtures.provider import provider
from src.infrastructure.execution.fixture_runner import FixtureRunner


def behavior(source: str, scenario: str, version: str, check_id: str, reproduce=False):
    try:
        with provider(scenario, version) as (url, interactions), FixtureRunner() as runner:
            runner.create_workspace(source)
            result = runner.run_command(
                "behavior", json.dumps({"base": url, "operations": OPERATIONS})
            )
        if result.exit_code or result.timed_out or result.truncated:
            return Check(
                id=check_id,
                outcome=Outcome.ERROR,
                reason="Consumer process failed or output exceeded limit",
                duration_ms=result.duration_ms,
            )
        actual = json.loads(result.stdout)
        return assess_behavior(
            actual,
            interactions,
            scenario,
            version,
            check_id,
            reproduce=reproduce,
            duration_ms=result.duration_ms,
        )
    except (OSError, ValueError) as exc:
        return Check(
            id=check_id,
            outcome=Outcome.UNAVAILABLE if isinstance(exc, OSError) else Outcome.ERROR,
            reason=f"Fixture check could not execute: {type(exc).__name__}",
        )


def static_check(source: str):
    with FixtureRunner() as runner:
        runner.create_workspace(source)
        result = runner.run_command("typecheck")
    return Check(
        id="STATIC",
        outcome=Outcome.PASS if result.exit_code == 0 and not result.timed_out else Outcome.FAIL,
        reason="TypeScript strict compiler check",
        observations={"exit_code": result.exit_code, "diagnostics": result.stdout[:4000]},
        duration_ms=result.duration_ms,
    )


class ExternalFixtureVerifier:
    behavior = staticmethod(behavior)
    static_check = staticmethod(static_check)

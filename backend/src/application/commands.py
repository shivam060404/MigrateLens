"""Entry-point-neutral fixture commands and their success criteria."""

from dataclasses import dataclass
from typing import Callable

from src.application.fixture_pipeline import ABSTENTIONS, SCENARIOS, SUPPORTED, FixturePipeline
from src.domain.evidence import validate_manifest


@dataclass(frozen=True)
class CommandResponse:
    payload: dict
    exit_code: int = 0


@dataclass
class FixtureCommands:
    pipeline_factory: Callable[[str, bool], FixturePipeline]

    def execute(
        self, command: str, scenario: str = "path", manifest: object = None
    ) -> CommandResponse:
        if command == "report":
            report = validate_manifest(manifest)
            return CommandResponse(
                {
                    "provenance": "unsigned local export; not authenticated",
                    "evidence": report.model_dump(mode="json"),
                }
            )
        if command in {"scan", "analyze"}:
            if scenario not in SUPPORTED:
                raise ValueError("Scan and analysis require a registered supported fixture")
            pipeline = self.pipeline_factory(scenario, False)
            result = (
                pipeline.detector.detect(pipeline.inputs.old_contract, pipeline.inputs.new_contract)
                if command == "scan"
                else pipeline.analyzer.analyze(pipeline.inputs.source, scenario)
            )
            return CommandResponse(result)
        if command not in {"demo", "repair", "verify", "benchmark"}:
            raise ValueError("Unknown fixture command")
        scenarios = SCENARIOS if command in {"demo", "benchmark"} else (scenario,)
        evidence = [self.pipeline_factory(name, False).run(name) for name in scenarios]
        failed = any(
            item.verdict
            != (
                "VERIFIED_FOR_DECLARED_SCOPE"
                if item.scenario in SUPPORTED
                else ABSTENTIONS[item.scenario][0]
            )
            for item in evidence
        )
        summary: dict = {
            "classification": "fictional development fixtures; not historical benchmark",
            "results": [
                {
                    "scenario": item.scenario,
                    "verdict": item.verdict,
                    "fingerprint": item.fingerprint,
                }
                for item in evidence
            ],
        }
        if command == "benchmark":
            wrong = self.pipeline_factory("path", True).run("path")
            checks = {check.id: check.outcome for check in wrong.checks}
            rejected = (
                len(checks) == len(wrong.checks)
                and wrong.verdict == "VALIDATION_FAILED"
                and checks.get("STATIC") == "PASS"
                and checks.get("REPAIR_NEW") == "FAIL"
            )
            summary.update(
                {
                    "wrong_patch_verdict": wrong.verdict,
                    "negative_control_fingerprint": wrong.fingerprint,
                    "negative_control_passed": rejected,
                    "comparison_arms": {
                        "A": "NOT RUN",
                        "B": "NOT RUN",
                        "C": "NOT RUN",
                        "D": "synthetic deterministic recipes only",
                    },
                }
            )
            failed = failed or not rejected
        return CommandResponse(summary, int(failed))

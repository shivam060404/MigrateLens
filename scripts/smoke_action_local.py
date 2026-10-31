"""Execute the composite Action proof step locally against fictional inputs."""

import json
import os
from pathlib import Path
import subprocess
import tempfile

import yaml

from src.config.paths import ROOT


def main() -> int:
    action = yaml.load((ROOT / "action.yml").read_text(), Loader=yaml.BaseLoader)
    proof = next(step for step in action["runs"]["steps"] if step.get("id") == "proof")
    with tempfile.TemporaryDirectory(prefix="migratelens-action-smoke-") as folder:
        output = Path(folder) / "github-output"
        environment = {
            **os.environ,
            "GITHUB_WORKSPACE": str(ROOT),
            "ML_ACTION_CONFIG": "oss/fixtures/registered-path-proof.json",
            "ML_ACTION_ENGINE": str(ROOT),
            "RUNNER_TEMP": folder,
            "GITHUB_OUTPUT": str(output),
        }
        result = subprocess.run(
            ["bash", "-e", "-c", proof["run"]],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            timeout=40,
            check=False,
        )
        if result.returncode:
            raise RuntimeError("Local composite proof step failed; no CI claim")
        key, path = output.read_text().strip().split("=", 1)
        if key != "metadata" or Path(path).parent != Path(folder):
            raise ValueError("Composite Action emitted unexpected metadata location")
        metadata = json.loads(Path(path).read_text())
        checks = metadata.get("checks")
        expected = {"BASELINE_OLD", "REPRO_NEW", "REPAIR_NEW", "REGRESSION", "STATIC", "POLICY"}
        if (
            metadata.get("schemaVersion") != "registered-export-1"
            or metadata.get("verdict") != "LOCAL_CHECKS_PASSED"
            or not isinstance(checks, list)
            or len(checks) != len(expected)
            or {item.get("id") for item in checks} != expected
            or any(item.get("outcome") != "PASS" for item in checks)
        ):
            raise ValueError("Composite Action metadata failed local contract check")
        environment["GITHUB_WORKSPACE"] = folder
        rejected = subprocess.run(
            ["bash", "-e", "-c", proof["run"]],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        if (
            rejected.returncode == 0
            or "outside the checked-out repository root" not in rejected.stderr
        ):
            raise ValueError("Composite Action did not reject mismatched workspace")
    print("LOCAL_ACTION_SMOKE_PASSED: six checks and workspace guard; no GitHub run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

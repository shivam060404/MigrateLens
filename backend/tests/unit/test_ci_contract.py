"""Keep the delivery baseline explicit and unprivileged."""

import re
import yaml

from src.config.paths import ROOT


def test_ci_has_required_gates_and_no_privileged_execution():
    raw = (ROOT / ".github/workflows/ci.yml").read_text()
    config = yaml.load(raw, Loader=yaml.BaseLoader)
    assert set(config["on"]) == {"push", "pull_request", "workflow_dispatch"}
    assert config["permissions"] == {"contents": "read"}
    assert "secrets." not in raw
    job = config["jobs"]["baseline"]
    assert int(job["timeout-minutes"]) <= 30
    steps = job["steps"]
    for step in steps:
        assert "continue-on-error" not in step
        if "uses" in step:
            assert re.search(r"@[a-f0-9]{40}$", step["uses"])
        if step.get("uses", "").startswith("actions/checkout@"):
            assert step["with"]["persist-credentials"] == "false"
    commands = "\n".join(step.get("run", "") for step in steps)
    for command in [
        "make bootstrap",
        "check-schemas",
        "lint",
        "typecheck",
        "test-unit",
        "test-security",
        "test-typescript",
        "test-integration",
        "build",
        "test-e2e",
        "benchmark-smoke",
    ]:
        assert command in commands


def test_fresh_typecheck_generates_routes_before_checking_types():
    makefile = (ROOT / "Makefile").read_text()
    target = makefile.split("\ntypecheck:\n", 1)[1].split("\n\n", 1)[0]
    assert target.index("scripts/frontend.mjs typegen") < target.index("frontend/tsconfig.json")


def test_standalone_oss_ci_has_no_python_or_repository_write_credentials():
    workflow = yaml.load((ROOT / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["oss"]
    steps = job["steps"]
    checkout = next(step for step in steps if step.get("uses", "").startswith("actions/checkout@"))
    assert checkout["with"]["persist-credentials"] == "false"
    commands = "\n".join(step.get("run", "") for step in steps)
    assert "make build-oss test-oss proof proof-registered" in commands
    artifact = next(step for step in steps if step.get("uses", "").startswith("actions/upload-artifact@"))
    assert "artifacts/registered-proof/" in artifact["with"]["path"]
    assert "setup-python" not in str(steps)
    assert "secrets." not in str(job)

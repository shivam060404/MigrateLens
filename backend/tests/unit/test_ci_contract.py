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
    artifact = next(
        step for step in steps if step.get("uses", "").startswith("actions/upload-artifact@")
    )
    assert artifact["with"]["path"] == "artifacts/evidence/registered.json"
    assert "artifacts/registered-proof/" not in str(steps)
    assert "setup-python" not in str(steps)
    assert "secrets." not in str(job)
    makefile = (ROOT / "Makefile").read_text()
    build_oss = makefile.split("\nbuild-oss:\n", 1)[1].split("\n\n", 1)[0]
    assert "oss/node_modules/typescript/bin/tsc" in build_oss


def test_attestation_is_opt_in_and_never_executes_consumer_code():
    workflow = yaml.load((ROOT / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)
    job = workflow["jobs"]["attest-metadata"]
    assert job["needs"] == "oss"
    assert "github.event_name == 'workflow_dispatch'" in job["if"]
    assert "github.ref == 'refs/heads/main'" in job["if"]
    assert "vars.ML_ENABLE_ATTESTATIONS == 'true'" in job["if"]
    assert job["permissions"] == {
        "contents": "read",
        "actions": "read",
        "id-token": "write",
        "attestations": "write",
    }
    assert "permissions" not in workflow["jobs"]["oss"]
    for step in job["steps"]:
        assert "run" not in step
        assert not step["uses"].startswith("actions/checkout@")
        assert re.search(r"@[a-f0-9]{40}$", step["uses"])
    assert job["steps"][0]["with"] == {"name": "registered-metadata", "path": "evidence"}
    assert job["steps"][1]["with"]["subject-path"] == "evidence/registered.json"


def test_composite_action_runs_only_registered_proof_in_caller_ci():
    action = yaml.load((ROOT / "action.yml").read_text(), Loader=yaml.BaseLoader)
    assert action["runs"]["using"] == "composite"
    assert set(action["inputs"]) == {"config"}
    assert action["outputs"]["metadata"]["value"] == "${{ steps.proof.outputs.metadata }}"
    steps = action["runs"]["steps"]
    assert re.search(r"@[a-f0-9]{40}$", steps[0]["uses"])
    assert "--frozen-lockfile --ignore-scripts --filter @migratelens/oss-core" in steps[1]["run"]
    assert "oss/node_modules/typescript/bin/tsc" in steps[2]["run"]
    proof = steps[3]
    assert proof["working-directory"] == "${{ github.workspace }}"
    assert "git rev-parse --show-toplevel" in proof["run"]
    assert "git config --local --get-regexp" in proof["run"]
    assert "cannot inspect checkout credentials" in proof["run"]
    assert " prove " in proof["run"]
    assert "--summary" in proof["run"]
    assert "publish" not in str(action)
    assert "secrets." not in str(action)


def test_ci_exercises_composite_action_without_repository_write_scope():
    workflow = yaml.load((ROOT / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["action-smoke"]
    steps = job["steps"]
    assert steps[0]["with"]["persist-credentials"] == "false"
    assert steps[1]["uses"] == "./"
    assert steps[1]["with"]["config"] == "oss/fixtures/registered-path-proof.json"
    assert "registered-export-1" in steps[2]["run"]
    assert "LOCAL_CHECKS_PASSED" in steps[2]["run"]
    assert steps[3]["with"]["path"] == "${{ steps.proof.outputs.metadata }}"
    assert "secrets." not in str(job)

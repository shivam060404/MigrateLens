"""Regression checks for clean setup and lock validation, using explicit tool doubles."""

import importlib.util
import json
import shutil

import pytest
import yaml

from src.config.paths import ROOT


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bootstrap_preserves_existing_environment(tmp_path, monkeypatch):
    module = load_script("bootstrap")
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin/python").touch()
    (tmp_path / "pyvenv.cfg").write_text("home = /test")
    monkeypatch.setattr(module.subprocess, "check_output", lambda *_a, **_k: "3.14.6\n")
    monkeypatch.setattr(module.subprocess, "run", lambda *_a, **_k: pytest.fail("Recreated venv"))
    assert module.prepare_environment(tmp_path) == tmp_path / "bin/python"


def test_bootstrap_refuses_non_venv_directory(tmp_path):
    with pytest.raises(ValueError, match="Refusing to replace"):
        load_script("bootstrap").prepare_environment(tmp_path)


def test_bootstrap_checks_existing_interpreter(tmp_path, monkeypatch):
    module = load_script("bootstrap")
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin/python").touch()
    (tmp_path / "pyvenv.cfg").touch()
    monkeypatch.setattr(module.subprocess, "check_output", lambda *_a, **_k: "3.13.0\n")
    with pytest.raises(ValueError, match="requires Python"):
        module.prepare_environment(tmp_path)


def test_ci_versions_match_bootstrap():
    module = load_script("bootstrap")
    workflow = yaml.load((ROOT / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)
    steps = workflow["jobs"]["baseline"]["steps"]
    for tool in ["python", "node"]:
        assert any(
            step.get("with", {}).get(f"{tool}-version") == module.VERSIONS[tool] for step in steps
        )
    commands = "\n".join(step.get("run", "") for step in steps)
    assert f"uv=={module.VERSIONS['uv']}" in commands
    assert f"pnpm@{module.VERSIONS['pnpm']}" in commands


@pytest.mark.parametrize("mutation", ["resolved", "extra", "integrity", "duplicate", "range"])
def test_lock_validator_rejects_drift(tmp_path, mutation):
    for name in [
        "backend/pyproject.toml",
        "backend/requirements.lock",
        "pnpm-lock.yaml",
        "package.json",
        "frontend/package.json",
        "backend/analyzer-ts/package.json",
        "oss/package.json",
    ]:
        dest = tmp_path / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, dest)
    lockpath = tmp_path / "pnpm-lock.yaml"
    lock = yaml.safe_load(lockpath.read_text())
    if mutation == "resolved":
        lock["importers"]["."]["devDependencies"]["typescript"]["version"] = "0.0.0"
    elif mutation == "extra":
        lock["importers"]["."]["dependencies"] = {
            "unexpected": {"specifier": "1.0.0", "version": "1.0.0"}
        }
    elif mutation == "integrity":
        lock["packages"]["typescript@5.9.3"]["resolution"] = {}
    elif mutation == "duplicate":
        path = tmp_path / "backend/requirements.lock"
        path.write_text(path.read_text() + "fastapi==0.139.0\n")
    else:
        path = tmp_path / "package.json"
        data = json.loads(path.read_text())
        data["devDependencies"]["typescript"] = "^5.9.3"
        path.write_text(json.dumps(data))
    lockpath.write_text(yaml.safe_dump(lock))
    with pytest.raises(ValueError):
        load_script("check_lockfiles").check(tmp_path)

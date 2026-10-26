"""Fail if manifests drift or offline resolution silently omits native build inputs."""

import json
import re
from pathlib import Path
import tomllib

import yaml
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]


def check(root: Path) -> None:
    project = tomllib.loads((root / "backend/pyproject.toml").read_text())
    locked = {}
    for line in (root / "backend/requirements.lock").read_text().splitlines():
        if line and not line.startswith("#"):
            requirement = Requirement(line)
            name = canonicalize_name(requirement.name)
            if name in locked:
                raise ValueError(f"Duplicate Python lock entry: {name}")
            specs = list(requirement.specifier)
            if (
                len(specs) != 1
                or specs[0].operator != "=="
                or "*" in specs[0].version
                or requirement.url
                or requirement.marker
                or requirement.extras
            ):
                raise ValueError(f"Python lock entry must be an unconditional exact pin: {name}")
            locked[name] = str(requirement.specifier)
    for spec in (
        project["project"]["dependencies"]
        + project["dependency-groups"]["dev"]
        + project["build-system"]["requires"]
    ):
        requirement = Requirement(spec)
        if locked.get(canonicalize_name(requirement.name)) != str(requirement.specifier):
            raise ValueError(f"Python manifest/lock mismatch: {requirement.name}")
    lock = yaml.safe_load((root / "pnpm-lock.yaml").read_text())
    if set(lock["importers"]) != {".", "frontend", "backend/analyzer-ts", "oss"}:
        raise ValueError("Unexpected or missing Node workspace importer")
    for workspace in [".", "frontend", "backend/analyzer-ts", "oss"]:
        manifest = json.loads((root / workspace / "package.json").read_text())
        importer = lock["importers"][workspace]
        for group in ["dependencies", "devDependencies"]:
            if set(importer.get(group, {})) != set(manifest.get(group, {})):
                raise ValueError(f"Node dependency set mismatch: {workspace}/{group}")
            for name, version in manifest.get(group, {}).items():
                entry = importer[group][name]
                if not re.fullmatch(r"\d+\.\d+\.\d+", version):
                    raise ValueError(f"Node dependency must be exact-pinned: {workspace}/{name}")
                if (
                    entry.get("specifier") != version
                    or entry.get("version", "").split("(")[0] != version
                ):
                    raise ValueError(f"Node manifest/lock mismatch: {workspace}/{name}")
                if f"{name}@{version}" not in lock["packages"]:
                    raise ValueError(f"Missing Node package resolution: {name}@{version}")
    for name, package in lock["packages"].items():
        if not package.get("resolution", {}).get("integrity", "").startswith("sha512-"):
            raise ValueError(f"Missing registry integrity: {name}")
    version = json.loads((root / "frontend/package.json").read_text())["dependencies"]["next"]
    for platform in ["darwin-arm64", "darwin-x64", "linux-x64-gnu", "linux-arm64-gnu"]:
        if f"@next/swc-{platform}@{version}" not in lock["packages"]:
            raise ValueError(f"Native Next.js dependency missing from lock: {platform}")
    print("PASS: direct manifests and native build dependencies are locked")


if __name__ == "__main__":
    try:
        check(ROOT)
    except (ValueError, KeyError) as exc:
        raise SystemExit(str(exc)) from exc

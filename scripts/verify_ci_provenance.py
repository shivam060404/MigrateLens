"""Verify registered metadata origin using a trusted, operator-installed GitHub CLI."""

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path


CHECKS = {"BASELINE_OLD", "REPRO_NEW", "REPAIR_NEW", "REGRESSION", "STATIC", "POLICY"}
HASH_FIELDS = {
    "registration",
    "oldSpec",
    "newSpec",
    "candidate",
    "patch",
    "testSuite",
    "policy",
    "implementation",
}


def unique_object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate metadata key")
        result[key] = value
    return result


def valid_hash(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", value) is not None


def read_metadata(artifact: Path) -> bytes:
    before = artifact.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError("Metadata must be a regular file, not a symlink or special file")
    if before.st_size > 65536:
        raise ValueError("Metadata exceeds byte budget")
    # NONBLOCK prevents a raced replacement with a FIFO from hanging admission.
    descriptor = os.open(artifact, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as source:
        opened = os.fstat(source.fileno())
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
            before.st_dev,
            before.st_ino,
        ):
            raise ValueError("Metadata file changed during admission")
        data = source.read(65537)
    if len(data) > 65536:
        raise ValueError("Metadata exceeds byte budget")
    return data


def reject_constant(value: str) -> None:
    raise ValueError("Non-JSON numeric constant")


def validate_metadata(metadata: object, fingerprint: str) -> None:
    keys = {
        "schemaVersion",
        "classification",
        "verdict",
        "fingerprint",
        "manifestHash",
        "identities",
        "checks",
    }
    if not isinstance(metadata, dict) or set(metadata) != keys:
        raise ValueError("Invalid metadata fields")
    if (
        metadata["schemaVersion"] != "registered-export-1"
        or metadata["classification"] != "unattested local metadata"
    ):
        raise ValueError("Unsupported metadata schema")
    if metadata["fingerprint"] != fingerprint or metadata["verdict"] != "LOCAL_CHECKS_PASSED":
        raise ValueError("Evidence fingerprint or local verdict mismatch")
    identities = metadata["identities"]
    if not isinstance(identities, dict) or set(identities) != HASH_FIELDS | {
        "sourceHashes",
        "runner",
    }:
        raise ValueError("Invalid identity fields")
    if not valid_hash(metadata["manifestHash"]) or any(
        not valid_hash(identities[key]) for key in HASH_FIELDS
    ):
        raise ValueError("Invalid identity hash")
    sources = identities["sourceHashes"]
    if not isinstance(sources, list) or len(sources) != 1 or not valid_hash(sources[0]):
        raise ValueError("Expected one registered source hash")
    if not isinstance(identities["runner"], str) or not re.fullmatch(
        r"node:v22\.\d+\.\d+;typescript:5\.9\.3;caller-local-unattested", identities["runner"]
    ):
        raise ValueError("Unsupported runner identity")
    checks = metadata["checks"]
    if not isinstance(checks, list) or len(checks) != len(CHECKS):
        raise ValueError("Incomplete check matrix")
    if any(
        not isinstance(check, dict)
        or set(check) != {"id", "outcome"}
        or check["outcome"] != "PASS"
        or not isinstance(check["id"], str)
        for check in checks
    ):
        raise ValueError("Invalid check matrix")
    if {check["id"] for check in checks} != CHECKS:
        raise ValueError("Missing or duplicate check")


def verify_origin(
    artifact: Path,
    repository: str,
    commit: str,
    fingerprint: str,
    artifact_hash: str,
    gh_binary: Path,
) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Invalid repository")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Expected exact source commit")
    if not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
        raise ValueError("Expected exact evidence fingerprint")
    data = read_metadata(artifact)
    actual_hash = "sha256:" + hashlib.sha256(data).hexdigest()
    if not valid_hash(artifact_hash) or actual_hash != artifact_hash:
        raise ValueError("Trusted artifact hash mismatch")
    try:
        metadata = json.loads(
            data.decode("utf-8"), object_pairs_hook=unique_object, parse_constant=reject_constant
        )
    except RecursionError as error:
        raise ValueError("Metadata exceeds parser depth") from error
    validate_metadata(metadata, fingerprint)
    if not gh_binary.is_absolute():
        raise ValueError("GitHub CLI path must be absolute")
    trusted_binary = gh_binary.resolve(strict=True)
    binary_mode = trusted_binary.stat().st_mode
    if (
        not stat.S_ISREG(binary_mode)
        or not os.access(trusted_binary, os.X_OK)
        or binary_mode & stat.S_IWOTH
        or trusted_binary.is_relative_to(Path(__file__).resolve().parents[1])
    ):
        raise ValueError("GitHub CLI must be an executable outside the repository")
    # Verify the exact bytes we inspected. Never execute repository code in this process.
    with tempfile.TemporaryDirectory(prefix="migratelens-origin-") as folder:
        snapshot = Path(folder) / "registered.json"
        snapshot.write_bytes(data)
        snapshot.chmod(0o400)
        workflow = f"{repository}/.github/workflows/ci.yml"
        command = [
            str(trusted_binary),
            "attestation",
            "verify",
            str(snapshot),
            "--hostname",
            "github.com",
            "--repo",
            repository,
            "--signer-workflow",
            workflow,
            "--signer-digest",
            commit,
            "--source-digest",
            commit,
            "--source-ref",
            "refs/heads/main",
            "--cert-identity",
            f"https://github.com/{workflow}@refs/heads/main",
            "--cert-oidc-issuer",
            "https://token.actions.githubusercontent.com",
            "--predicate-type",
            "https://slsa.dev/provenance/v1",
            "--deny-self-hosted-runners",
        ]
        result = subprocess.run(
            command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60, check=False
        )
        if result.returncode != 0 or snapshot.read_bytes() != data:
            raise ValueError("GitHub attestation verification failed")
    return {
        "status": "CI_ORIGIN_VERIFIED",
        "artifactHash": "sha256:" + hashlib.sha256(data).hexdigest(),
        "repository": repository,
        "commit": commit,
        "fingerprint": fingerprint,
        "publicationAuthorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--fingerprint", required=True)
    parser.add_argument("--artifact-hash", required=True)
    parser.add_argument("--gh-binary", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = verify_origin(
            args.artifact,
            args.repo,
            args.commit,
            args.fingerprint,
            args.artifact_hash,
            args.gh_binary,
        )
    except ValueError, OSError, subprocess.TimeoutExpired:
        parser.exit(1, "Origin verification failed; no publication authorized\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

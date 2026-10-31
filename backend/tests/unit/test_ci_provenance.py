import json
import hashlib
import os
from types import SimpleNamespace

import pytest

from scripts.verify_ci_provenance import verify_origin, validate_metadata, read_metadata


def metadata_fixture():
    digest = "sha256:" + "d" * 64
    return {
        "schemaVersion": "registered-export-1",
        "classification": "unattested local metadata",
        "fingerprint": "a" * 64,
        "verdict": "LOCAL_CHECKS_PASSED",
        "manifestHash": digest,
        "identities": {
            **{
                key: digest
                for key in [
                    "registration",
                    "oldSpec",
                    "newSpec",
                    "candidate",
                    "patch",
                    "testSuite",
                    "policy",
                    "implementation",
                ]
            },
            "sourceHashes": [digest],
            "runner": "node:v22.23.1;typescript:5.9.3;caller-local-unattested",
        },
        "checks": [
            {"id": key, "outcome": "PASS"}
            for key in ["BASELINE_OLD", "REPRO_NEW", "REPAIR_NEW", "REGRESSION", "STATIC", "POLICY"]
        ],
    }


def test_origin_enforces_exact_identity_and_never_authorizes_publication(tmp_path, monkeypatch):
    artifact = tmp_path / "metadata.json"
    artifact.write_text(json.dumps(metadata_fixture()))
    gh_binary = tmp_path / "gh"
    gh_binary.write_text("trusted test executable")
    gh_binary.chmod(0o755)
    digest = "sha256:" + hashlib.sha256(artifact.read_bytes()).hexdigest()
    calls = []

    def verifier(command, **kwargs):
        calls.append(command)
        assert kwargs["timeout"] == 60
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("scripts.verify_ci_provenance.subprocess.run", verifier)
    result = verify_origin(artifact, "example/repo", "b" * 40, "a" * 64, digest, gh_binary)
    assert result["publicationAuthorized"] is False
    command = calls[0]
    assert command[0] == str(gh_binary)
    for flag in ("--source-digest", "--signer-digest"):
        assert command[command.index(flag) + 1] == "b" * 40
    assert command[command.index("--source-ref") + 1] == "refs/heads/main"
    assert (
        command[command.index("--cert-identity") + 1]
        == "https://github.com/example/repo/.github/workflows/ci.yml@refs/heads/main"
    )
    with pytest.raises(ValueError, match="mismatch"):
        verify_origin(artifact, "example/repo", "b" * 40, "c" * 64, digest, gh_binary)
    with pytest.raises(ValueError, match="artifact hash mismatch"):
        verify_origin(artifact, "example/repo", "b" * 40, "a" * 64, "sha256:" + "0" * 64, gh_binary)
    assert len(calls) == 1
    monkeypatch.setattr(
        "scripts.verify_ci_provenance.subprocess.run", lambda *a, **k: SimpleNamespace(returncode=1)
    )
    with pytest.raises(ValueError, match="verification failed"):
        verify_origin(artifact, "example/repo", "b" * 40, "a" * 64, digest, gh_binary)


@pytest.mark.parametrize("kind", ["relative", "missing", "not_executable", "world_writable"])
def test_origin_rejects_untrusted_cli_path(tmp_path, monkeypatch, kind):
    artifact = tmp_path / "metadata.json"
    artifact.write_text(json.dumps(metadata_fixture()))
    digest = "sha256:" + hashlib.sha256(artifact.read_bytes()).hexdigest()
    binary = tmp_path / "gh"
    if kind != "missing":
        binary.write_text("test binary")
        binary.chmod(
            0o777 if kind == "world_writable" else 0o644 if kind == "not_executable" else 0o755
        )
    if kind == "relative":
        binary = binary.relative_to(tmp_path)
    monkeypatch.setattr(
        "scripts.verify_ci_provenance.subprocess.run",
        lambda *a, **k: pytest.fail("Untrusted CLI invoked"),
    )
    with pytest.raises((ValueError, OSError)):
        verify_origin(artifact, "example/repo", "b" * 40, "a" * 64, digest, binary)


@pytest.mark.parametrize("fault", ["missing", "duplicate", "failed", "extra", "bad_hash"])
def test_metadata_rejects_incomplete_or_altered_evidence(fault):
    metadata = metadata_fixture()
    if fault == "missing":
        metadata["checks"].pop()
    elif fault == "duplicate":
        metadata["checks"][0] = metadata["checks"][1]
    elif fault == "failed":
        metadata["checks"][0]["outcome"] = "FAIL"
    elif fault == "extra":
        metadata["source"] = "unexpected source data"
    else:
        metadata["identities"]["policy"] = "unbound"
    with pytest.raises(ValueError):
        validate_metadata(metadata, "a" * 64)


@pytest.mark.parametrize("kind", ["symlink", "fifo", "directory", "oversized"])
def test_metadata_file_admission_is_bounded(tmp_path, kind):
    path = tmp_path / "artifact"
    if kind == "symlink":
        target = tmp_path / "target"
        target.write_text("{}")
        path.symlink_to(target)
    elif kind == "fifo":
        os.mkfifo(path)
    elif kind == "directory":
        path.mkdir()
    else:
        path.write_bytes(b"x" * 65537)
    with pytest.raises(ValueError):
        read_metadata(path)


@pytest.mark.parametrize(
    "data", [b'{"x":1,"x":2}', b'{"x":NaN}', b"\xff", b"[" * 2000 + b"]" * 2000]
)
def test_malformed_metadata_never_invokes_verifier(tmp_path, monkeypatch, data):
    artifact = tmp_path / "metadata.json"
    artifact.write_bytes(data)

    def unexpected(*args, **kwargs):
        pytest.fail("Malformed metadata reached GitHub verifier")

    monkeypatch.setattr("scripts.verify_ci_provenance.subprocess.run", unexpected)
    with pytest.raises(ValueError):
        verify_origin(
            artifact,
            "example/repo",
            "b" * 40,
            "a" * 64,
            "sha256:" + hashlib.sha256(data).hexdigest(),
            tmp_path / "gh",
        )

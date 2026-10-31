"""Installer rejects altered archives and never extracts unrelated files."""

import hashlib
import io
import tarfile
from pathlib import Path

import pytest

from scripts.install_oasdiff import install


def archive_with(name: str, payload: bytes) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        member = tarfile.TarInfo(name)
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))
    return output.getvalue()


def test_installs_only_verified_executable(tmp_path: Path) -> None:
    archive = archive_with("oasdiff", b"fixture-binary")
    destination = tmp_path / "bin" / "oasdiff"
    digest = install(destination, archive, hashlib.sha256(archive).hexdigest())
    assert destination.read_bytes() == b"fixture-binary"
    assert digest == hashlib.sha256(b"fixture-binary").hexdigest()


def test_rejects_digest_mismatch_and_unexpected_member(tmp_path: Path) -> None:
    archive = archive_with("oasdiff", b"altered")
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        install(tmp_path / "oasdiff", archive, "0" * 64)
    with pytest.raises(ValueError, match="missing or invalid"):
        wrong = archive_with("../oasdiff", b"payload")
        install(tmp_path / "oasdiff", wrong, hashlib.sha256(wrong).hexdigest())
    assert not (tmp_path / "oasdiff").exists()

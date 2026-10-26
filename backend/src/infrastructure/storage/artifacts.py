"""Local development blob adapter with exact object identity and content verification."""

import hashlib
import os
import stat
from pathlib import Path
from uuid import UUID

from src.domain.control import Conflict, NotFound

MAX_ARTIFACT_BYTES = 10_000_000


class LocalArtifactStore:
    def __init__(self, root: Path):
        self.root = root.resolve()

    @staticmethod
    def key(tenant: UUID, artifact_id: UUID) -> str:
        return f"{tenant}/{artifact_id}"

    def _path(self, tenant: UUID, artifact_id: UUID, key: str) -> Path:
        if key != self.key(tenant, artifact_id):
            raise Conflict("Artifact object identity mismatch")
        directory = self.root / str(tenant)
        if directory.exists() and directory.resolve() != self.root / str(tenant):
            raise Conflict("Artifact directory is not trusted")
        return directory / str(artifact_id)

    def put(self, tenant: UUID, artifact_id: UUID, content: bytes) -> tuple[str, str, int]:
        if len(content) > MAX_ARTIFACT_BYTES:
            raise ValueError("Artifact exceeds the local size limit")
        key = self.key(tenant, artifact_id)
        path = self._path(tenant, artifact_id, key)
        path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        if path.parent.resolve() != self.root / str(tenant):
            raise Conflict("Artifact directory is not trusted")
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, "wb") as output:
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return key, hashlib.sha256(content).hexdigest(), len(content)

    def read(self, tenant: UUID, artifact_id: UUID, key: str, sha256: str, size: int) -> bytes:
        if size < 0 or size > MAX_ARTIFACT_BYTES:
            raise Conflict("Artifact size metadata is invalid")
        path = self._path(tenant, artifact_id, key)
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        except FileNotFoundError as exc:
            raise NotFound("Artifact content not found") from exc
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size != size:
                raise Conflict("Artifact size or type mismatch")
            with os.fdopen(fd, "rb") as source:
                fd = -1
                content = source.read(MAX_ARTIFACT_BYTES + 1)
        finally:
            if fd >= 0:
                os.close(fd)
        if len(content) != size or hashlib.sha256(content).hexdigest() != sha256:
            raise Conflict("Artifact digest mismatch")
        return content

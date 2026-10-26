"""Actual local bytes and service authorization, without a database claim."""

from contextlib import contextmanager
from uuid import uuid4

import pytest

from src.application.control import ControlService
from src.domain.control import AccessDenied, Conflict, Membership, Principal, Role
from src.infrastructure.storage.artifacts import LocalArtifactStore


class ArtifactSession:
    def __init__(self, tenant, repository_id, metadata):
        self.membership = Membership(tenant, "alice", Role.VIEWER)
        self.tenant = tenant
        self.repository_id = repository_id
        self.metadata = metadata
        self.granted = True

    @contextmanager
    def session(self, principal, tenant):
        assert principal == Principal("alice") and tenant == self.tenant
        yield self

    def artifact(self, artifact_id):
        return self.metadata if artifact_id == self.metadata["id"] else None

    def case(self, case_id):
        return (
            {"repository_id": self.repository_id} if case_id == self.metadata["case_id"] else None
        )

    def repository_granted(self, repository_id):
        return self.granted and repository_id == self.repository_id


def test_authorized_artifact_download_verifies_bytes_and_hides_key(tmp_path):
    store = LocalArtifactStore(tmp_path)
    tenant, artifact_id, case_id, repo = (uuid4() for _ in range(4))
    content = b"synthetic evidence\n"
    key, digest, size = store.put(tenant, artifact_id, content)
    metadata = {
        "id": artifact_id,
        "case_id": case_id,
        "object_key": key,
        "sha256": digest,
        "size_bytes": size,
        "created_at": "now",
    }
    port = ArtifactSession(tenant, repo, metadata)
    service = ControlService(port, artifact_reader=store)
    assert service.download_artifact(Principal("alice"), tenant, artifact_id) == content
    assert "object_key" not in service.artifact(Principal("alice"), tenant, artifact_id)
    port.granted = False
    with pytest.raises(AccessDenied):
        service.download_artifact(Principal("alice"), tenant, artifact_id)


def test_object_identity_tamper_and_duplicate_writes_fail(tmp_path):
    store = LocalArtifactStore(tmp_path)
    tenant, artifact_id = uuid4(), uuid4()
    key, digest, size = store.put(tenant, artifact_id, b"evidence")
    with pytest.raises(FileExistsError):
        store.put(tenant, artifact_id, b"replace")
    with pytest.raises(Conflict, match="identity"):
        store.read(tenant, artifact_id, "../other", digest, size)
    with pytest.raises(Conflict, match="digest"):
        store.read(tenant, artifact_id, key, "a" * 64, size)
    (tmp_path / str(tenant) / str(artifact_id)).write_bytes(b"changed!")
    with pytest.raises(Conflict, match="digest"):
        store.read(tenant, artifact_id, key, digest, size)


def test_symlinked_tenant_directory_is_rejected(tmp_path):
    store = LocalArtifactStore(tmp_path / "objects")
    tenant, artifact_id = uuid4(), uuid4()
    store.root.mkdir()
    (store.root / str(tenant)).symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(Conflict, match="directory"):
        store.put(tenant, artifact_id, b"evidence")

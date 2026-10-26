"""Release-owned fixture admission. This controller module is trusted application code.

Digests pin reviewed bytes, not user-controlled repository configuration. Changing
fixtures requires reviewing this allowlist. It does not contain arbitrary host code.
"""

from pathlib import Path

from src.config.paths import ROOT
from src.domain.execution_policy import ExecutionDenied, authorize_repository
from src.domain.models import digest

# Filled from the reviewed bundled inputs below; never regenerated at runtime.
INPUT_DIGESTS: dict[str, str] = {
    # Readable exclusion fixture; deliberately absent from CANDIDATE_DIGESTS.
    "fixtures/consumers/unsupported/dynamic.ts": "43835bec83b97318d14b7db5467ac6ceeae98d76f222a40379dbb1741569f22b",
    "fixtures/consumers/northstar/src/integrations/customer/client.ts": "42da31964e1bb8050ed8022ad4c65129f798c4c8d027b928f234f69d3a560201",
    "fixtures/consumers/bridge.mjs": "11079c12a07344c3f74de19be88c9815efe96cb117cbb5941cfecc03950bb378",
    "fixtures/provider/mappings.json": "ef8c9e9fd69dddd1f241a39e2a1d0e4cce4c23f7c8dea52ab66d0b83bccfdfaa",
    "backend/analyzer-ts/analyze.mjs": "9beff152bc696a58ebfc14c2dce5c8904cdb3fee71cd74974aa69ca68ab1a2df",
    "backend/analyzer-ts/recipes.mjs": "de6223a062c95ea8f735abb3d159f8398db1957fd8295aea60e8529baa96ecae",
}
CANDIDATE_DIGESTS: frozenset[str] = frozenset(
    [
        "42da31964e1bb8050ed8022ad4c65129f798c4c8d027b928f234f69d3a560201",
        "a66b98b4cdd260298a473f73b0b453025baabea85c9b05bc9467e9d6fbcd4e98",
        "b28403701ca5d2fc3e1c5ee162e22dc953e4885862f1ac32ff0842ff65c6ce49",
        "b8183ec01aadff966fcc2cb43b87f1e7396ec3bc5476c544da18954a032386aa",
        "8f43f74c47683f98def210629cebf3780011d82c7782cf1afc1d85f7bfa1d501",
    ]
)


def assert_no_symlinks(path: Path) -> None:
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ExecutionDenied("Symlinked fixture or artifact paths are not allowed")


def read_reviewed(relative: str) -> bytes:
    if relative not in INPUT_DIGESTS:
        raise ExecutionDenied("Path is not a release-approved fixture input")
    path = ROOT / relative
    assert_no_symlinks(path)
    data = path.read_bytes()
    if digest(data) != INPUT_DIGESTS[relative]:
        raise ExecutionDenied(
            "Bundled fixture integrity mismatch; review required before execution"
        )
    return data


def authorize_source(source: str, repository: str = "bundled:northstar-consumer") -> None:
    authorize_repository(repository)
    if digest(source.encode()) not in CANDIDATE_DIGESTS:
        raise ExecutionDenied("Unreviewed source is not executable by the host fixture adapter")

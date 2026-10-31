"""Install the pinned oasdiff release after verifying its archive digest.

This installer only extracts the named executable; it never runs archive scripts.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import platform
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

VERSION = "1.34.1"
ARCHIVES = {
    ("Darwin", "arm64"): (
        "darwin_all",
        "64948ba30c5555d3d15b95a7f3eda22fa83c15cf37fd4dad1720c0deb0a07cb5",
    ),
    ("Darwin", "x86_64"): (
        "darwin_all",
        "64948ba30c5555d3d15b95a7f3eda22fa83c15cf37fd4dad1720c0deb0a07cb5",
    ),
    ("Linux", "x86_64"): (
        "linux_amd64",
        "75775f65b0adebd26a8e013af51a799342dfdc6262d89efa9e3b7bdf89657d90",
    ),
    ("Linux", "aarch64"): (
        "linux_arm64",
        "e8f99bbf102a4b7f235104da72d0b9d67702e78622d1d4d37169e698ee90a249",
    ),
}
MAX_ARCHIVE_BYTES = 16_000_000
MAX_BINARY_BYTES = 40_000_000


def install(destination: Path, archive_bytes: bytes, expected_sha256: str) -> str:
    if len(archive_bytes) > MAX_ARCHIVE_BYTES:
        raise ValueError("oasdiff archive exceeds size budget")
    actual = hashlib.sha256(archive_bytes).hexdigest()
    if actual != expected_sha256:
        raise ValueError("oasdiff archive SHA256 mismatch")
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as archive:
        members = [member for member in archive.getmembers() if member.name == "oasdiff"]
        if len(members) != 1 or not members[0].isfile() or members[0].size > MAX_BINARY_BYTES:
            raise ValueError("oasdiff executable missing or invalid")
        source = archive.extractfile(members[0])
        if source is None:
            raise ValueError("oasdiff executable unreadable")
        binary = source.read(MAX_BINARY_BYTES + 1)
        if len(binary) != members[0].size or len(binary) > MAX_BINARY_BYTES:
            raise ValueError("oasdiff executable exceeds size budget")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staged = destination.with_name(destination.name + ".tmp")
    try:
        staged.write_bytes(binary)
        staged.chmod(0o755)
        os.replace(staged, destination)
    finally:
        staged.unlink(missing_ok=True)
    return hashlib.sha256(binary).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=Path(".local/bin/oasdiff"))
    args = parser.parse_args()
    system = platform.system()
    machine = platform.machine()
    entry = ARCHIVES.get((system, machine))
    if entry is None:
        raise SystemExit(f"Unsupported oasdiff platform: {system}/{machine}")
    platform_name, expected = entry
    asset = f"oasdiff_{VERSION}_{platform_name}.tar.gz"
    url = f"https://github.com/oasdiff/oasdiff/releases/download/v{VERSION}/{asset}"
    request = urllib.request.Request(url, headers={"User-Agent": "MigrateLens-pinned-installer/1"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            archive = response.read(MAX_ARCHIVE_BYTES + 1)
    except urllib.error.URLError:
        raise SystemExit(
            f"Cannot fetch pinned oasdiff {VERSION} release asset; check network/DNS and retry"
        ) from None
    binary_hash = install(args.destination, archive, expected)
    print(f"Installed oasdiff {VERSION} at {args.destination} (binary sha256:{binary_hash})")


if __name__ == "__main__":
    main()

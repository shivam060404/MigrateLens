"""Host adapter restricted to release-approved fictional code. NOT a customer sandbox."""

import shutil
import tempfile
from pathlib import Path

from src.config.paths import ROOT
from src.domain.execution_policy import ExecutionDenied
from src.infrastructure.execution.process import CommandResult, ProcessExecutor
from src.infrastructure.security.fixture_admission import (
    assert_no_symlinks,
    authorize_source,
    read_reviewed,
)


class FixtureRunner:
    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix="migratelens-fixture-")).resolve()
        self.executor = ProcessExecutor()
        self.initialized = False

    def create_workspace(self, source: str) -> None:
        authorize_source(source)
        bridge = read_reviewed("fixtures/consumers/bridge.mjs")
        assert_no_symlinks(self.root)
        if self.initialized:
            raise ValueError("Workspace already initialized")
        (self.root / "client.ts").write_text(source)
        (self.root / "bridge.mjs").write_bytes(bridge)
        self.initialized = True

    def install_dependencies(self):
        return {"status": "NOT_APPLICABLE", "reason": "Fixture consumer uses Node built-ins only"}

    def run_command(self, command_id: str, stdin: str = "", timeout: float = 15) -> CommandResult:
        if command_id not in {"behavior", "typecheck"}:
            raise ExecutionDenied("Unregistered command ID")
        if not self.initialized:
            raise ExecutionDenied("No approved workspace")
        assert_no_symlinks(self.root)
        expected_files = {"client.ts", "bridge.mjs"}
        if {file.name for file in self.root.iterdir()} != expected_files:
            raise ExecutionDenied("Unexpected workspace files")
        for name in expected_files:
            assert_no_symlinks(self.root / name)
        authorize_source((self.root / "client.ts").read_text())
        if (self.root / "bridge.mjs").read_bytes() != read_reviewed(
            "fixtures/consumers/bridge.mjs"
        ):
            raise ExecutionDenied("Bridge integrity mismatch")
        node = shutil.which("node")
        if node is None:
            raise RuntimeError("Node.js 22 is required")
        command = (
            [
                node,
                "--experimental-strip-types",
                "--disable-warning=ExperimentalWarning",
                "bridge.mjs",
            ]
            if command_id == "behavior"
            else [
                node,
                str(ROOT / "node_modules/typescript/bin/tsc"),
                "--noEmit",
                "--strict",
                "--skipLibCheck",
                "--target",
                "ES2022",
                "--lib",
                "ES2022,DOM",
                "client.ts",
            ]
        )
        return self.executor.run(command, self.root, stdin, timeout=timeout)

    def apply_patch(self, source: str) -> None:
        authorize_source(source)
        assert_no_symlinks(self.root / "client.ts")
        (self.root / "client.ts").write_text(source)

    def collect_artifacts(self):
        assert_no_symlinks(self.root / "client.ts")
        return {"source": (self.root / "client.ts").read_text()}

    def cancel(self) -> None:
        self.executor.cancel()

    def destroy(self) -> None:
        self.cancel()
        shutil.rmtree(self.root, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.destroy()

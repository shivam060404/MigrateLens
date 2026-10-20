"""Node transport consumes frozen source bytes; it does not select repository files."""

import json
import shutil

from src.config.paths import ANALYZER, ROOT
from src.infrastructure.execution.process import ProcessExecutor
from src.infrastructure.security.fixture_admission import authorize_source, read_reviewed


class TypeScriptFixtureAnalyzer:
    def analyze(self, source: str, scenario: str, repair: bool = False) -> dict:
        authorize_source(source)
        read_reviewed("backend/analyzer-ts/analyze.mjs")
        read_reviewed("backend/analyzer-ts/recipes.mjs")
        node = shutil.which("node")
        if node is None:
            raise RuntimeError("Node.js 22 is required")
        result = ProcessExecutor().run(
            [node, str(ANALYZER), scenario, "repair" if repair else "analyze"],
            ROOT,
            stdin=source,
            timeout=20,
        )
        if result.exit_code or result.timed_out or result.truncated or result.cancelled:
            raise RuntimeError("TypeScript analyzer failed its bounded execution profile")
        data = json.loads(result.stdout)
        if not isinstance(data, dict) or data.get("schema_version") != "1":
            raise ValueError("Invalid analyzer result")
        if repair:
            authorize_source(data["source"])
        return data

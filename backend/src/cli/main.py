"""Argument parsing, transport I/O and presentation only; decisions live in application."""

import argparse
import json
import sys
from pathlib import Path

from src.application.fixture_pipeline import SCENARIOS
from src.bootstrap import create_commands


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="MigrateLens fictional local reference — no live publication"
    )
    parser.add_argument(
        "command", choices=["demo", "scan", "analyze", "repair", "verify", "report", "benchmark"]
    )
    parser.add_argument("--scenario", choices=SCENARIOS, default="path")
    parser.add_argument("--output", type=Path, default=Path("artifacts"))
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = None
        if args.command == "report":
            if args.manifest is None:
                parser.error("report requires --manifest")
            if args.manifest.stat().st_size > 1_000_000:
                raise ValueError("Manifest exceeds byte budget")
            manifest = json.loads(args.manifest.read_text())
        response = create_commands(args.output).execute(args.command, args.scenario, manifest)
        print(json.dumps(response.payload, indent=2))
        return response.exit_code
    except (ValueError, OSError, RuntimeError) as exc:
        print(
            json.dumps({"error": {"code": "LOCAL_COMMAND_FAILED", "message": str(exc)}}),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

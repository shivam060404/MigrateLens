"""Install the pinned toolchain dependencies without replacing an existing venv."""

import argparse
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = {"python": "3.14.6", "node": "22.23.1", "uv": "0.11.32", "pnpm": "11.11.0"}


def check_toolchain() -> None:
    actual = {"python": platform.python_version()}
    for tool in ("node", "uv", "pnpm"):
        output = subprocess.check_output([tool, "--version"], text=True).strip()
        actual[tool] = output.split()[1] if tool == "uv" else output.removeprefix("v")
    for tool, version in VERSIONS.items():
        if actual[tool] != version:
            raise ValueError(f"{tool} {version} required; found {actual[tool]}")


def prepare_environment(venv: Path) -> Path:
    python = venv / "bin/python"
    if venv.exists():
        if not (venv / "pyvenv.cfg").is_file() or not python.is_file():
            raise ValueError(f"Refusing to replace invalid environment: {venv}")
    else:
        subprocess.run(["uv", "venv", "--python", sys.executable, str(venv)], check=True, cwd=ROOT)
    version = subprocess.check_output(
        [str(python), "-c", "import platform; print(platform.python_version())"], text=True
    ).strip()
    if version != VERSIONS["python"]:
        raise ValueError(f"Environment requires Python {VERSIONS['python']}; found {version}")
    return python


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--venv", type=Path, default=Path(".venv"))
    args = parser.parse_args()
    try:
        check_toolchain()
        python = prepare_environment(args.venv.absolute())
        for command in [
            ["uv", "pip", "sync", "--python", str(python), "backend/requirements.lock"],
            ["uv", "pip", "check", "--python", str(python)],
            ["pnpm", "install", "--frozen-lockfile", "--ignore-scripts"],
        ]:
            subprocess.run(command, cwd=ROOT, check=True)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Bootstrap failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

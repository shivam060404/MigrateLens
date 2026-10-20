"""Run the local backend and frontend together; stop both on exit or child failure."""

import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
children: list[subprocess.Popen] = []


def stop(*_):
    raise KeyboardInterrupt


def main():
    signal.signal(signal.SIGTERM, stop)
    env = {**os.environ, "PYTHONPATH": str(ROOT / "backend"), "NEXT_TELEMETRY_DISABLED": "1"}
    try:
        for command in [
            [
                sys.executable,
                "-m",
                "uvicorn",
                "src.api.app:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            ["pnpm", "--filter", "@migratelens/frontend", "dev"],
        ]:
            children.append(subprocess.Popen(command, cwd=ROOT, env=env, start_new_session=True))
        while all(child.poll() is None for child in children):
            time.sleep(0.25)
        return next((child.returncode for child in children if child.returncode is not None), 1)
    except KeyboardInterrupt:
        return 130
    finally:
        for child in children:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()


if __name__ == "__main__":
    raise SystemExit(main())

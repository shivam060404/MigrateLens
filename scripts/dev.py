"""Foreground local supervisor. Stop requests use a nonce, never an untrusted PID."""

import argparse
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".local/dev-state.json"
STOP = ROOT / ".local/dev-stop.json"


def stop_handler(*_):
    raise KeyboardInterrupt


def request_stop() -> int:
    if not STATE.exists():
        print("No managed development supervisor is registered.")
        return 0
    state = json.loads(STATE.read_text())
    STOP.write_text(json.dumps({"nonce": state["nonce"]}))
    deadline = time.monotonic() + 8
    while STATE.exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    if STATE.exists():
        print(
            "Supervisor did not acknowledge shutdown. Inspect stale .local/dev-state.json; no PID was signalled.",
            file=sys.stderr,
        )
        return 1
    print("Development supervisor and owned child processes stopped.")
    return 0


def supervise() -> int:
    signal.signal(signal.SIGTERM, stop_handler)
    env = {**os.environ, "PYTHONPATH": str(ROOT / "backend"), "NEXT_TELEMETRY_DISABLED": "1"}
    STATE.parent.mkdir(parents=True, exist_ok=True)
    nonce = secrets.token_hex(32)
    children: list[subprocess.Popen] = []
    try:
        with STATE.open("x") as state:
            json.dump({"pid": os.getpid(), "nonce": nonce}, state)
    except FileExistsError:
        print(
            "A supervisor is registered. Run make down or inspect stale .local/dev-state.json.",
            file=sys.stderr,
        )
        return 1
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
            if STOP.exists():
                try:
                    if json.loads(STOP.read_text()).get("nonce") == nonce:
                        return 0
                except ValueError, OSError:
                    pass
            time.sleep(0.25)
        return next((child.returncode for child in children if child.returncode is not None), 1)
    except KeyboardInterrupt:
        return 130
    finally:
        for child in children:
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        STOP.unlink(missing_ok=True)
        STATE.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stop", action="store_true")
    args = parser.parse_args()
    return request_stop() if args.stop else supervise()


if __name__ == "__main__":
    raise SystemExit(main())

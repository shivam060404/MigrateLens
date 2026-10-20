"""Bounded POSIX process transport for trusted command profiles. Not an OS sandbox."""

import os
import signal
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    truncated: bool
    duration_ms: int
    cancelled: bool = False


def stop_group(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


class ProcessExecutor:
    """Only trusted adapters may construct command arrays; never exposed by the API."""

    def __init__(self):
        self.cancelled = threading.Event()

    def cancel(self) -> None:
        self.cancelled.set()

    def run(
        self,
        command: list[str],
        cwd: Path,
        stdin: str = "",
        *,
        timeout: float = 15,
        max_output: int = 65536,
    ) -> CommandResult:
        if self.cancelled.is_set():
            raise RuntimeError("CANCELLED")
        if not 0 < timeout <= 30 or not 0 < max_output <= 1_000_000:
            raise ValueError("Invalid process budget")
        if len(stdin.encode()) > 65536:
            raise ValueError("Input exceeds process budget")
        started = time.monotonic()
        timed_out = truncated = False
        with (
            tempfile.TemporaryFile() as incoming,
            tempfile.TemporaryFile() as out,
            tempfile.TemporaryFile() as err,
        ):
            incoming.write(stdin.encode())
            incoming.seek(0)
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env={"PATH": os.defpath, "HOME": str(cwd), "LANG": "C.UTF-8"},
                stdin=incoming,
                stdout=out,
                stderr=err,
                start_new_session=True,
                close_fds=True,
            )
            try:
                while process.poll() is None:
                    timed_out = time.monotonic() - started >= timeout
                    truncated = (
                        max(os.fstat(out.fileno()).st_size, os.fstat(err.fileno()).st_size)
                        > max_output
                    )
                    if timed_out or truncated or self.cancelled.is_set():
                        stop_group(process)
                        break
                    self.cancelled.wait(0.01)
                process.wait(timeout=3)
            finally:
                # Also removes descendants when the leader has already exited.
                stop_group(process)
                if process.poll() is None:
                    process.wait(timeout=3)
            truncated = (
                truncated
                or max(os.fstat(out.fileno()).st_size, os.fstat(err.fileno()).st_size) > max_output
            )
            out.seek(0)
            err.seek(0)
            return CommandResult(
                process.returncode,
                out.read(max_output).decode(errors="replace"),
                err.read(max_output).decode(errors="replace"),
                timed_out,
                truncated,
                int((time.monotonic() - started) * 1000),
                self.cancelled.is_set(),
            )

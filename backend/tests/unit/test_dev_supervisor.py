"""Supervisor lifecycle tests with process doubles, not running web servers."""

import importlib.util
import json
import signal

from src.config.paths import ROOT


def load_supervisor(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("dev_supervisor", ROOT / "scripts/dev.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(module, "STOP", tmp_path / "stop.json")
    monkeypatch.setattr(module.signal, "signal", lambda *_: None)
    return module


def test_child_failure_cleans_only_owned_process_groups(tmp_path, monkeypatch):
    supervisor = load_supervisor(tmp_path, monkeypatch)
    children = []
    signals = []

    class Child:
        returncode = 1

        def __init__(self, *_args, **kwargs):
            assert kwargs["start_new_session"] is True
            self.pid = 100 + len(children)
            self.waited = False
            children.append(self)

        def poll(self):
            return self.returncode

        def wait(self, **_kwargs):
            self.waited = True
            return self.returncode

    monkeypatch.setattr(supervisor.subprocess, "Popen", Child)
    monkeypatch.setattr(supervisor.os, "killpg", lambda pid, sig: signals.append((pid, sig)))
    assert supervisor.supervise() == 1
    assert signals == [(100, signal.SIGTERM), (101, signal.SIGTERM)]
    assert all(child.waited for child in children)
    assert not supervisor.STATE.exists()
    assert not supervisor.STOP.exists()


def test_stop_requests_nonce_without_trusting_stored_pid(tmp_path, monkeypatch):
    supervisor = load_supervisor(tmp_path, monkeypatch)
    supervisor.STATE.write_text(json.dumps({"pid": 1, "nonce": "test-only"}))

    def acknowledge(_):
        assert json.loads(supervisor.STOP.read_text()) == {"nonce": "test-only"}
        supervisor.STATE.unlink()

    def forbidden_signal(*_):
        raise AssertionError("Untrusted stored PID was used to signal a process")

    monkeypatch.setattr(supervisor.time, "sleep", acknowledge)
    monkeypatch.setattr(supervisor.os, "killpg", forbidden_signal)
    monkeypatch.setattr(supervisor.os, "kill", forbidden_signal)
    assert supervisor.request_stop() == 0


def test_down_without_supervisor_has_no_side_effects(tmp_path, monkeypatch):
    supervisor = load_supervisor(tmp_path, monkeypatch)
    assert supervisor.request_stop() == 0
    assert not list(tmp_path.iterdir())

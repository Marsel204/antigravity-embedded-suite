"""Tests for skills/embedded-micro/scripts/serial_monitor.py.

Uses a pseudo-terminal pair as a stand-in for the ESP32 USB serial port,
so the suite runs without hardware attached.
"""

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/embedded-micro/scripts/serial_monitor.py"


def load_module():
    spec = importlib.util.spec_from_file_location("serial_monitor", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sm = load_module()


# ---------------------------------------------------------------- port pick
def _ports(*entries):
    return {"detected_ports": [{"port": e} for e in entries]}


def test_pick_port_prefers_single_usb_port():
    data = _ports(
        {"address": "/dev/ttyS4", "properties": {}},
        {"address": "/dev/ttyACM0", "properties": {"vid": "0x1A86", "pid": "0x55D3"}},
    )
    assert sm.pick_port(data) == "/dev/ttyACM0"


def test_pick_port_none_when_only_builtin_uart():
    assert sm.pick_port(_ports({"address": "/dev/ttyS4", "properties": {}})) is None


def test_pick_port_ambiguous_raises():
    data = _ports(
        {"address": "/dev/ttyACM0", "properties": {"vid": "0x1A86"}},
        {"address": "/dev/ttyUSB0", "properties": {"vid": "0x10C4"}},
    )
    with pytest.raises(sm.PortError):
        sm.pick_port(data)


def test_pick_port_accepts_legacy_list_format():
    legacy = [{"port": {"address": "/dev/ttyUSB0", "properties": {"vid": "0x10C4"}}}]
    assert sm.pick_port(legacy) == "/dev/ttyUSB0"


# ---------------------------------------------------------- terminal argv
@pytest.mark.parametrize(
    "term,expected_prefix",
    [
        ("alacritty", ["alacritty", "--title", "T", "-e"]),
        ("foot", ["foot", "--title", "T"]),
        ("kitty", ["kitty", "--title", "T"]),
        ("xdg-terminal-exec", ["xdg-terminal-exec"]),
        ("xterm", ["xterm", "-T", "T", "-e"]),
    ],
)
def test_terminal_command(term, expected_prefix):
    argv = ["python3", "x.py", "run"]
    cmd = sm.terminal_command(term, "T", argv)
    assert cmd[: len(expected_prefix)] == expected_prefix
    assert cmd[-3:] == argv


def test_terminal_command_unknown_raises():
    with pytest.raises(sm.TerminalError):
        sm.terminal_command("not-a-terminal", "T", ["x"])


# ---------------------------------------------------------- line logger
def test_line_logger_splits_partial_chunks(tmp_path):
    log = tmp_path / "s.log"
    lg = sm.LineLogger(log)
    lg.feed(b"RAW: 31")
    lg.feed(b"50\r\nRAW: 1180\n")
    lg.close()
    lines = log.read_text().splitlines()
    assert [l.split("] ", 1)[1] for l in lines] == ["RAW: 3150", "RAW: 1180"]
    assert lines[0].startswith("[")


# ---------------------------------------------------- pty integration
@pytest.fixture
def pty_port():
    master, slave = os.openpty()
    name = os.ttyname(slave)
    yield master, name
    os.close(master)
    os.close(slave)


def _env(tmp_path):
    env = os.environ.copy()
    env["EMBEDDED_MICRO_STATE_DIR"] = str(tmp_path)
    return env


def _cli(tmp_path, *args, timeout=10):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        env=_env(tmp_path), capture_output=True, text=True, timeout=timeout,
    )


def test_capture_is_bounded_and_reads_lines(tmp_path, pty_port):
    master, name = pty_port
    proc = subprocess.Popen(
        [sys.executable, str(SCRIPT), "capture", "--port", name, "--seconds", "2"],
        env=_env(tmp_path), stdout=subprocess.PIPE, text=True,
    )
    time.sleep(0.6)
    os.write(master, b"RAW: 42\nhello\n")
    t0 = time.time()
    out, _ = proc.communicate(timeout=6)
    assert time.time() - t0 < 4
    assert "RAW: 42" in out and "hello" in out


def test_run_logs_then_pause_releases_port_and_resume(tmp_path, pty_port):
    master, name = pty_port
    run = subprocess.Popen(
        [sys.executable, str(SCRIPT), "run", "--port", name],
        env=_env(tmp_path), stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + 5
        while time.time() < deadline and _cli(tmp_path, "status", "--port", name).returncode != 0:
            time.sleep(0.2)
        assert _cli(tmp_path, "status", "--port", name).returncode == 0

        os.write(master, b"boot ok\n")
        time.sleep(0.6)
        tail = _cli(tmp_path, "tail", "--port", name, "-n", "5")
        assert "boot ok" in tail.stdout

        r = _cli(tmp_path, "pause", "--port", name)
        assert r.returncode == 0, r.stderr
        assert "paused" in r.stdout.lower()

        r = _cli(tmp_path, "resume", "--port", name)
        assert r.returncode == 0
        os.write(master, b"after resume\n")
        time.sleep(1.2)
        assert "after resume" in _cli(tmp_path, "tail", "--port", name, "-n", "5").stdout

        assert _cli(tmp_path, "stop", "--port", name).returncode == 0
        run.wait(timeout=5)
        assert _cli(tmp_path, "status", "--port", name).returncode != 0
    finally:
        if run.poll() is None:
            run.kill()


def test_pause_without_monitor_is_noop(tmp_path):
    r = _cli(tmp_path, "pause", "--port", "/dev/ttyFAKE9")
    assert r.returncode == 0
    assert "not running" in r.stdout.lower()

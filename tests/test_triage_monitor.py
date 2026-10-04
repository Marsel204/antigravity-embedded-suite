"""Tests for embedded-triage serial monitor and crash analyzer integration.

Verifies:
1. skills/embedded-triage/scripts/serial_monitor.py operates identically and cooperatively.
2. analyze_crash.py seamlessly reads from the active serial monitor log when a monitor
   is running, avoiding [Errno 16] Device or resource busy errors.
3. analyze_crash.py falls back to bounded serial reading when no monitor is active.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

TRIAGE_MONITOR = Path(__file__).resolve().parents[1] / "skills/embedded-triage/scripts/serial_monitor.py"
MICRO_MONITOR = Path(__file__).resolve().parents[1] / "skills/embedded-micro/scripts/serial_monitor.py"
ANALYZE_CRASH = Path(__file__).resolve().parents[1] / "skills/embedded-triage/scripts/analyze_crash.py"


def _env(tmp_path):
    env = os.environ.copy()
    env["EMBEDDED_MICRO_STATE_DIR"] = str(tmp_path)
    env["EMBEDDED_SERIAL_STATE_DIR"] = str(tmp_path)
    return env


@pytest.fixture
def pty_port():
    master, slave = os.openpty()
    name = os.ttyname(slave)
    yield master, name
    os.close(master)
    os.close(slave)


def test_triage_monitor_script_exists():
    assert TRIAGE_MONITOR.is_file(), f"{TRIAGE_MONITOR} must exist"
    assert os.access(TRIAGE_MONITOR, os.X_OK), f"{TRIAGE_MONITOR} must be executable"


def test_triage_and_micro_share_state_directory(tmp_path):
    # Verify triage serial_monitor reports status against same state directory
    r_micro = subprocess.run(
        [sys.executable, str(MICRO_MONITOR), "status", "--port", "/dev/ttyFAKE1"],
        env=_env(tmp_path), capture_output=True, text=True,
    )
    r_triage = subprocess.run(
        [sys.executable, str(TRIAGE_MONITOR), "status", "--port", "/dev/ttyFAKE1"],
        env=_env(tmp_path), capture_output=True, text=True,
    )
    assert r_micro.returncode == r_triage.returncode
    assert "not running" in r_triage.stdout.lower()


def test_analyze_crash_reads_from_active_monitor(tmp_path, pty_port):
    master, name = pty_port
    # Start triage monitor on pty_port
    run_proc = subprocess.Popen(
        [sys.executable, str(TRIAGE_MONITOR), "run", "--port", name],
        env=_env(tmp_path), stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        # Wait for monitor status to become active
        deadline = time.time() + 5
        while time.time() < deadline:
            res = subprocess.run(
                [sys.executable, str(TRIAGE_MONITOR), "status", "--port", name],
                env=_env(tmp_path), capture_output=True, text=True,
            )
            if res.returncode == 0:
                break
            time.sleep(0.2)
        assert res.returncode == 0

        # Simulate crash dump emitted into serial
        crash_msg = (
            b"Guru Meditation Error: Core  0 panic'ed (LoadProhibited). Exception was unhandled.\n"
            b"Backtrace: 0x40081234 0x40085678\n"
        )
        os.write(master, crash_msg)
        time.sleep(0.8)

        # analyze_crash on same port should read active monitor without port conflict
        analyzer = subprocess.run(
            [sys.executable, str(ANALYZE_CRASH), "--port", name, "--timeout", "2"],
            env=_env(tmp_path), capture_output=True, text=True, timeout=8,
        )
        assert analyzer.returncode == 0, analyzer.stderr
        assert "LoadProhibited" in analyzer.stdout
        assert "Null Pointer Dereference" in analyzer.stdout
    finally:
        subprocess.run([sys.executable, str(TRIAGE_MONITOR), "stop", "--port", name], env=_env(tmp_path))
        if run_proc.poll() is None:
            run_proc.kill()


def test_analyze_crash_reads_direct_pty_when_no_monitor(tmp_path, pty_port):
    master, name = pty_port
    proc = subprocess.Popen(
        [sys.executable, str(ANALYZE_CRASH), "--port", name, "--timeout", "2"],
        env=_env(tmp_path), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    time.sleep(0.5)
    os.write(master, b"Brownout detector was triggered\n")
    out, err = proc.communicate(timeout=6)
    assert proc.returncode == 0, err
    assert "Brownout Reset Detected" in out

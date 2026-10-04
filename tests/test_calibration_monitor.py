"""Tests for sensor-calibration serial monitor and compute_calibration integration.

Verifies:
1. skills/sensor-calibration/scripts/serial_monitor.py exists, is executable, and cooperates.
2. compute_calibration.py --sample-port reads from the active monitor stream when a monitor
   is running, preventing [Errno 16] Device or resource busy errors.
3. compute_calibration.py falls back to direct serial sampling when no monitor is active.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

CALIB_MONITOR = Path(__file__).resolve().parents[1] / "skills/sensor-calibration/scripts/serial_monitor.py"
MICRO_MONITOR = Path(__file__).resolve().parents[1] / "skills/embedded-micro/scripts/serial_monitor.py"
COMPUTE_CALIB = Path(__file__).resolve().parents[1] / "skills/sensor-calibration/scripts/compute_calibration.py"


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


def test_calib_monitor_script_exists():
    assert CALIB_MONITOR.is_file(), f"{CALIB_MONITOR} must exist"
    assert os.access(CALIB_MONITOR, os.X_OK), f"{CALIB_MONITOR} must be executable"


def test_calib_and_micro_share_state_directory(tmp_path):
    r_micro = subprocess.run(
        [sys.executable, str(MICRO_MONITOR), "status", "--port", "/dev/ttyFAKE2"],
        env=_env(tmp_path), capture_output=True, text=True,
    )
    r_calib = subprocess.run(
        [sys.executable, str(CALIB_MONITOR), "status", "--port", "/dev/ttyFAKE2"],
        env=_env(tmp_path), capture_output=True, text=True,
    )
    assert r_micro.returncode == r_calib.returncode
    assert "not running" in r_calib.stdout.lower()


def test_compute_calibration_reads_from_active_monitor(tmp_path, pty_port):
    master, name = pty_port
    # Start monitor on pty_port
    run_proc = subprocess.Popen(
        [sys.executable, str(CALIB_MONITOR), "run", "--port", name],
        env=_env(tmp_path), stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + 5
        while time.time() < deadline:
            res = subprocess.run(
                [sys.executable, str(CALIB_MONITOR), "status", "--port", name],
                env=_env(tmp_path), capture_output=True, text=True,
            )
            if res.returncode == 0:
                break
            time.sleep(0.2)
        assert res.returncode == 0

        # Feed raw samples into serial
        for i in range(10):
            os.write(master, f"RAW: {1000 + i * 5}\n".encode())
            time.sleep(0.05)
        time.sleep(0.6)

        # compute_calibration on same port should read active monitor without port conflict
        sampler = subprocess.run(
            [sys.executable, str(COMPUTE_CALIB), "--sample-port", name, "--count", "5"],
            env=_env(tmp_path), capture_output=True, text=True, timeout=8,
        )
        assert sampler.returncode == 0, sampler.stderr
        assert "[DATA FILTER]" in sampler.stdout
        assert "Mean:" in sampler.stdout
    finally:
        subprocess.run([sys.executable, str(CALIB_MONITOR), "stop", "--port", name], env=_env(tmp_path))
        if run_proc.poll() is None:
            run_proc.kill()


def test_compute_calibration_reads_direct_pty_when_no_monitor(tmp_path, pty_port):
    master, name = pty_port
    proc = subprocess.Popen(
        [sys.executable, str(COMPUTE_CALIB), "--sample-port", name, "--count", "3"],
        env=_env(tmp_path), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    time.sleep(0.5)
    for i in range(5):
        os.write(master, f"RAW: {500 + i * 10}\n".encode())
        time.sleep(0.05)
    out, err = proc.communicate(timeout=6)
    assert proc.returncode == 0, err
    assert "[DATA FILTER]" in out
    assert "Mean:" in out

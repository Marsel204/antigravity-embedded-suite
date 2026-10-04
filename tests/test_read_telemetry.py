"""Tests for read-telemetry skill and process_telemetry.py utility.

Verifies:
1. Run-length deduplication of repetitive serial streams.
2. Statistical aggregation across numeric keys (min, max, mean, stddev, latest).
3. Delta-change filtering with configurable thresholds.
4. Parsing of Key-Value, JSON, RAW, and labeled pin formats.
5. Live streaming capture over virtual serial ports (os.openpty).
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/read-telemetry/scripts/process_telemetry.py"


@pytest.fixture
def pty_port():
    master, slave = os.openpty()
    name = os.ttyname(slave)
    yield master, name
    os.close(master)
    os.close(slave)


def test_script_exists_and_executable():
    assert SCRIPT.is_file(), f"{SCRIPT} must exist"
    assert os.access(SCRIPT, os.X_OK), f"{SCRIPT} must be executable"


def test_deduplicate_collapses_repeated_lines(tmp_path):
    log_file = tmp_path / "raw.log"
    log_file.write_text(
        "TEMP: 24.5, HUM: 60\n" * 15 +
        "TEMP: 25.0, HUM: 60\n" * 3 +
        "TEMP: 25.0, HUM: 60\n"
    )
    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--file", str(log_file), "--mode", "dedup"],
        capture_output=True, text=True, check=True,
    )
    out = res.stdout.strip().splitlines()
    assert len(out) <= 3
    assert any("[x15 repeated]" in line or "(x15)" in line for line in out)
    assert any("TEMP: 25.0, HUM: 60" in line for line in out)


def test_statistical_summary_computes_metrics(tmp_path):
    log_file = tmp_path / "telemetry.log"
    log_file.write_text(
        "ANALOG: GPIO1=100, GPIO2=10\n"
        "ANALOG: GPIO1=200, GPIO2=20\n"
        "ANALOG: GPIO1=300, GPIO2=30\n"
    )
    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--file", str(log_file), "--mode", "summary", "--format", "json"],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(res.stdout)
    assert "GPIO1" in data
    assert data["GPIO1"]["count"] == 3
    assert data["GPIO1"]["min"] == 100.0
    assert data["GPIO1"]["max"] == 300.0
    assert data["GPIO1"]["mean"] == 200.0
    assert data["GPIO1"]["latest"] == 300.0

    assert "GPIO2" in data
    assert data["GPIO2"]["min"] == 10.0
    assert data["GPIO2"]["max"] == 30.0
    assert data["GPIO2"]["mean"] == 20.0


def test_delta_filtering_ignores_subthreshold_changes(tmp_path):
    log_file = tmp_path / "stream.log"
    log_file.write_text(
        "VOLTAGE: 3.30\n"
        "VOLTAGE: 3.31\n"
        "VOLTAGE: 3.32\n"
        "VOLTAGE: 3.55\n"
        "VOLTAGE: 3.56\n"
    )
    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--file", str(log_file), "--mode", "deltas", "--threshold", "0.20"],
        capture_output=True, text=True, check=True,
    )
    lines = res.stdout.strip().splitlines()
    # Initial line 3.30 emitted, then only 3.55 (delta >= 0.20)
    assert len(lines) == 2
    assert "3.30" in lines[0]
    assert "3.55" in lines[1]


def test_json_and_raw_parsing(tmp_path):
    log_file = tmp_path / "multi.log"
    log_file.write_text(
        '{"sensor": "temp", "val": 22.4}\n'
        '{"sensor": "temp", "val": 24.6}\n'
    )
    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--file", str(log_file), "--mode", "summary", "--format", "json"],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(res.stdout)
    assert "val" in data
    assert data["val"]["count"] == 2
    assert data["val"]["mean"] == 23.5


def test_live_pty_capture(pty_port):
    master, name = pty_port
    proc = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--port", name, "--duration", "2", "--mode", "summary", "--format", "json"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    time.sleep(0.5)
    for v in [50, 150, 250]:
        os.write(master, f"RAW: {v}\n".encode())
        time.sleep(0.1)

    out, err = proc.communicate(timeout=5)
    assert proc.returncode == 0, err
    data = json.loads(out)
    key = "RAW" if "RAW" in data else "val"
    assert key in data
    assert data[key]["count"] == 3
    assert data[key]["mean"] == 150.0

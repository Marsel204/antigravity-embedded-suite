"""CLI regressions for pin validation, calibration output, and offline crash input."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
PIN = ROOT / "skills/embedded-micro/scripts/validate_pins.py"
CAL = ROOT / "skills/sensor-calibration/scripts/compute_calibration.py"
CRASH = ROOT / "skills/embedded-triage/scripts/analyze_crash.py"


def run(script, *args, **kwargs):
    return subprocess.run([sys.executable, str(script), *args],
                          text=True, capture_output=True, timeout=10, **kwargs)


@pytest.mark.parametrize("args,code", [
    (["--platform", "esp23", "--pins", "4"], 2),
    (["--platform", "esp32", "--pins=-1,20,24,99"], 1),
    (["--platform", "esp32s3", "--pins=22,25,49"], 1),
    (["--pins", "SDA"], 2),
])
def test_invalid_pins(args, code):
    result = run(PIN, *args)
    assert result.returncode == code
    assert "error" in (result.stdout + result.stderr).lower()
    assert "Traceback" not in result.stderr


POINTS = ["--mode", "two-point", "--raw1", "0", "--phys1", "-40",
          "--raw2", "1000", "--phys2", "125"]


def test_two_point_preserves_physical_range():
    result = run(CAL, *POINTS)
    assert result.returncode == 0
    assert "CALIB_SLOPE  = 0.16500000f" in result.stdout
    assert "CALIB_OFFSET = -40.0000f" in result.stdout
    assert "return val;" in result.stdout
    assert "constrain(" not in result.stdout


def test_two_point_optional_clamp():
    result = run(CAL, *POINTS, "--clamp", "-40", "125")
    assert result.returncode == 0
    assert "return constrain(val, -40.0f, 125.0f);" in result.stdout


@pytest.mark.parametrize("weight", ["0", "-1", "nan", "inf"])
def test_invalid_weight(weight):
    result = run(CAL, "--mode", "tare-scale", "--tare", "100",
                 "--known-raw", "300", "--known-weight", weight)
    assert result.returncode == 2
    assert "positive and finite" in result.stderr
    assert "Traceback" not in result.stderr


def test_identical_raw_points():
    result = run(CAL, "--mode", "two-point", "--raw1", "1", "--phys1", "0",
                 "--raw2", "1", "--phys2", "100")
    assert result.returncode == 2
    assert "distinct" in result.stderr
    assert "Traceback" not in result.stderr


def test_duplicate_poly_x():
    result = run(CAL, "--mode", "poly3", "--x1", "0", "--y1", "1",
                 "--x2", "0", "--y2", "6", "--x3", "2", "--y3", "17")
    assert result.returncode == 2
    assert "distinct" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("args", [[], ["--file", "-"]])
def test_crash_stdin_never_imports_serial(tmp_path, args):
    # Fail loudly even on an attempted import, before any port could be opened.
    (tmp_path / "serial.py").write_text('raise RuntimeError("SERIAL IMPORT FORBIDDEN")')
    env = os.environ.copy()
    env["PYTHONPATH"] = str(tmp_path)
    env["EMBEDDED_SERIAL_STATE_DIR"] = str(tmp_path / "state")
    result = run(CRASH, *args, input="Brownout detector was triggered\n", env=env)
    assert result.returncode == 0, result.stderr
    assert "Hardware Brownout Reset Detected" in result.stdout
    assert "SERIAL IMPORT FORBIDDEN" not in result.stdout + result.stderr
    assert not (tmp_path / "state").exists()


@pytest.mark.parametrize("args", [[], ["--file", "-"]])
def test_crash_empty_stdin_reports_missing_input(tmp_path, args):
    (tmp_path / "serial.py").write_text('raise RuntimeError("SERIAL IMPORT FORBIDDEN")')
    env = os.environ.copy()
    env["PYTHONPATH"] = str(tmp_path)
    result = run(CRASH, *args, input="", env=env)
    assert result.returncode == 2
    assert "No crash log input" in result.stderr
    assert "SERIAL IMPORT FORBIDDEN" not in result.stdout + result.stderr


def test_pin_platform_accepts_hyphenated_name():
    result = run(PIN, "--platform", "ESP32-S3", "--pins", "4,5")
    assert result.returncode == 0, result.stderr
    assert "ESP32S3" in result.stdout

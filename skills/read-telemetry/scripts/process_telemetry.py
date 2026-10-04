#!/usr/bin/env python3
"""
process_telemetry.py - Token-Efficient Microcontroller Telemetry Processor
Preprocesses high-frequency sensor streams: deduplication, statistical summaries, and delta filtering.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Enable sibling module imports if embedded-micro / embedded-triage scripts are nearby
sys.path.insert(0, str(Path(__file__).resolve().parent))
for skill_dir in [
    Path(__file__).resolve().parents[2] / "embedded-micro/scripts",
    Path(__file__).resolve().parents[2] / "embedded-triage/scripts",
    Path.home() / ".gemini/config/skills/embedded-micro/scripts",
]:
    if skill_dir.is_dir():
        sys.path.insert(0, str(skill_dir))

try:
    from serial_monitor import Paths, running_pid, resolve_port
except ImportError:
    Paths = None
    running_pid = None
    resolve_port = None


def clean_line_content(line: str) -> str:
    """Strip monitor timestamp prefix: [YYYY-MM-DD HH:MM:SS]."""
    return re.sub(r"^\[\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\]\s*", "", line.strip())


def extract_numeric_metrics(line: str) -> Dict[str, float]:
    """Extract numeric metrics from line (JSON, Key-Value, or RAW)."""
    clean = clean_line_content(line)
    metrics: Dict[str, float] = {}

    # Try JSON
    if clean.startswith("{") and clean.endswith("}"):
        try:
            data = json.loads(clean)
            if isinstance(data, dict):
                for k, v in data.items():
                    try:
                        metrics[str(k)] = float(v)
                    except (ValueError, TypeError):
                        pass
                if metrics:
                    return metrics
        except json.JSONDecodeError:
            pass

    # Try Key=Value or Key: Value pairs
    # Matches patterns like GPIO1=701, TEMP: 24.5, RAW: 100
    kv_matches = re.findall(r"([A-Za-z0-9_]+)\s*[:=]\s*(-?\d+(?:\.\d+)?)", clean)
    if kv_matches:
        for k, v in kv_matches:
            try:
                metrics[k] = float(v)
            except ValueError:
                pass
        if metrics:
            return metrics

    # Standalone single numeric value
    single = re.match(r"^(-?\d+(?:\.\d+)?)$", clean)
    if single:
        try:
            metrics["val"] = float(single.group(1))
        except ValueError:
            pass

    return metrics


# ---------------------------------------------------------------- Modes
def run_dedup(lines: List[str]) -> List[str]:
    """Run-length encode consecutive identical lines."""
    if not lines:
        return []
    result: List[str] = []
    current_line = clean_line_content(lines[0])
    count = 1

    for raw in lines[1:]:
        cleaned = clean_line_content(raw)
        if cleaned == current_line:
            count += 1
        else:
            if count > 1:
                result.append(f"[x{count} repeated] {current_line}")
            else:
                result.append(current_line)
            current_line = cleaned
            count = 1

    if count > 1:
        result.append(f"[x{count} repeated] {current_line}")
    else:
        result.append(current_line)
    return result


def run_deltas(lines: List[str], threshold: float) -> List[str]:
    """Filter lines to only emit when numeric values change by >= threshold."""
    result: List[str] = []
    last_values: Dict[str, float] = {}

    for raw in lines:
        cleaned = clean_line_content(raw)
        metrics = extract_numeric_metrics(cleaned)
        if not metrics:
            result.append(cleaned)
            continue

        changed = False
        if not last_values:
            changed = True
        else:
            for k, v in metrics.items():
                if k not in last_values or abs(v - last_values[k]) >= threshold:
                    changed = True
                    break

        if changed:
            result.append(cleaned)
            last_values.update(metrics)

    return result


def compute_statistics(lines: List[str]) -> Dict[str, Dict[str, float]]:
    """Compute count, min, max, mean, stddev, latest for numeric channels."""
    buckets: Dict[str, List[float]] = {}
    for raw in lines:
        metrics = extract_numeric_metrics(raw)
        for k, v in metrics.items():
            buckets.setdefault(k, []).append(v)

    summary: Dict[str, Dict[str, float]] = {}
    for k, values in buckets.items():
        if not values:
            continue
        n = len(values)
        min_v = min(values)
        max_v = max(values)
        mean_v = sum(values) / n
        variance = sum((x - mean_v) ** 2 for x in values) / n if n > 1 else 0.0
        stddev_v = math.sqrt(variance)
        summary[k] = {
            "count": n,
            "min": round(min_v, 4),
            "max": round(max_v, 4),
            "mean": round(mean_v, 4),
            "stddev": round(stddev_v, 4),
            "latest": round(values[-1], 4),
        }
    return summary


def format_summary_table(summary: Dict[str, Dict[str, float]]) -> str:
    """Format statistical summary as a token-bounded markdown table."""
    if not summary:
        return "No numeric telemetry channels detected."
    lines = [
        "| Channel / Key | Samples | Min | Max | Mean | StdDev | Latest |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for k, s in summary.items():
        lines.append(
            f"| `{k}` | {s['count']} | {s['min']} | {s['max']} | {s['mean']:.2f} | {s['stddev']:.2f} | {s['latest']} |"
        )
    return "\n".join(lines)


# ----------------------------------------------------------- Data Ingestion
def ingest_lines(
    file_path: Optional[str] = None,
    port: Optional[str] = None,
    baud: int = 115200,
    duration: float = 3.0,
    max_lines: Optional[int] = None,
) -> List[str]:
    """Ingest lines from file, shared monitor stream, or serial port."""
    if file_path:
        if file_path == "-":
            lines = [l.rstrip("\r\n") for l in sys.stdin]
        else:
            with open(file_path, "r", errors="ignore") as f:
                lines = [l.rstrip("\r\n") for l in f]
        return lines[:max_lines] if max_lines else lines

    # Serial port ingestion
    target_port = port or "auto"
    if resolve_port:
        try:
            target_port = resolve_port(target_port)
        except Exception:
            pass

    # Check for active monitor stream
    paths = Paths(target_port) if Paths else None
    pid = running_pid(paths) if (paths and running_pid) else None

    lines: List[str] = []
    if pid is not None and paths and paths.log.exists():
        start_time = time.time()
        initial_pos = paths.log.stat().st_size
        with open(paths.log, "r", errors="ignore") as f:
            f.seek(initial_pos)
            while time.time() - start_time < duration:
                l = f.readline()
                if l:
                    lines.append(l.rstrip("\r\n"))
                    if max_lines and len(lines) >= max_lines:
                        break
                else:
                    time.sleep(0.05)
    else:
        try:
            import serial
        except ImportError:
            print("[ERROR] pyserial is required for direct serial capture.", file=sys.stderr)
            sys.exit(1)

        try:
            with serial.Serial(target_port, baud, timeout=1.0) as ser:
                time.sleep(0.2)
                ser.reset_input_buffer()
                start_time = time.time()
                while time.time() - start_time < duration:
                    l = ser.readline().decode("utf-8", errors="ignore").rstrip("\r\n")
                    if l:
                        lines.append(l)
                        if max_lines and len(lines) >= max_lines:
                            break
        except Exception as e:
            print(f"[ERROR] Failed to read from {target_port}: {e}", file=sys.stderr)
            sys.exit(1)

    return lines


# --------------------------------------------------------------------- Main
def main():
    parser = argparse.ArgumentParser(description="Microcontroller Telemetry Preprocessor")
    parser.add_argument("--mode", choices=["summary", "dedup", "deltas", "snapshot"], default="summary")
    parser.add_argument("--format", choices=["table", "json", "text"], default="table")
    parser.add_argument("--file", help="Input log file path or '-' for stdin")
    parser.add_argument("--port", help="Serial port to sample from (default: auto)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("--duration", type=float, default=3.0, help="Live capture duration in seconds")
    parser.add_argument("--lines", type=int, help="Max lines to ingest")
    parser.add_argument("--threshold", type=float, default=1.0, help="Delta filter sensitivity threshold")

    args = parser.parse_args()

    # If stdin has piped data and no source specified
    file_path = args.file
    if not file_path and not args.port and not sys.stdin.isatty():
        file_path = "-"

    raw_lines = ingest_lines(
        file_path=file_path,
        port=args.port,
        baud=args.baud,
        duration=args.duration,
        max_lines=args.lines,
    )

    if not raw_lines:
        if args.format == "json":
            print(json.dumps({}))
        else:
            print("No telemetry data received.")
        return

    if args.mode == "summary":
        summary = compute_statistics(raw_lines)
        if args.format == "json":
            print(json.dumps(summary, indent=2))
        else:
            print(format_summary_table(summary))

    elif args.mode == "dedup":
        collapsed = run_dedup(raw_lines)
        if args.format == "json":
            print(json.dumps(collapsed, indent=2))
        else:
            print("\n".join(collapsed))

    elif args.mode == "deltas":
        filtered = run_deltas(raw_lines, args.threshold)
        if args.format == "json":
            print(json.dumps(filtered, indent=2))
        else:
            print("\n".join(filtered))

    elif args.mode == "snapshot":
        summary = compute_statistics(raw_lines)
        latest_snapshot = {k: s["latest"] for k, s in summary.items()}
        if args.format == "json":
            print(json.dumps(latest_snapshot, indent=2))
        else:
            pairs = [f"{k}={v}" for k, v in latest_snapshot.items()]
            print("SNAPSHOT: " + ", ".join(pairs))


if __name__ == "__main__":
    main()

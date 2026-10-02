#!/usr/bin/env python3
"""
compute_calibration.py - Sensor Calibration & Automated Sampling Utility
Harvests raw serial samples over USB, filters outliers, and computes linear/tare/polynomial calibration with C++ code generation.
"""

import sys
import re
import math
import argparse

def sample_from_serial(port: str, baud: int = 115200, count: int = 20) -> list[float]:
    try:
        import serial
        import time
    except ImportError:
        print("[ERROR] pyserial is required for live sampling. Install via: pip install pyserial", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Opening {port} at {baud} baud to harvest {count} raw samples...")
    samples = []
    start_time = time.time()
    max_timeout = 8.0

    try:
        with serial.Serial(port, baud, timeout=1.0) as ser:
            time.sleep(0.5)
            ser.reset_input_buffer()

            while len(samples) < count and (time.time() - start_time < max_timeout):
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                
                match = re.search(r'(?:RAW:\s*)?(-?\d+(?:\.\d+)?)', line, re.IGNORECASE)
                if match:
                    try:
                        val = float(match.group(1))
                        samples.append(val)
                    except ValueError:
                        continue

    except Exception as e:
        print(f"[ERROR] Failed to read from {port}: {e}", file=sys.stderr)
        sys.exit(1)

    if not samples:
        print(f"[ERROR] No valid data received from {port} within timeout.", file=sys.stderr)
        sys.exit(1)

    print(f"[OK] Successfully captured {len(samples)} samples over {port}.")
    return samples

def filter_samples(raw_values: list[float]) -> tuple[float, float, list[float]]:
    if not raw_values:
        return 0.0, 0.0, []
    
    mean = sum(raw_values) / len(raw_values)
    variance = sum((x - mean) ** 2 for x in raw_values) / len(raw_values)
    stddev = math.sqrt(variance)

    filtered = [x for x in raw_values if abs(x - mean) <= 2.0 * stddev] if stddev > 0 else raw_values
    filtered_mean = sum(filtered) / len(filtered) if filtered else mean

    return filtered_mean, stddev, filtered

def compute_two_point(raw1: float, phys1: float, raw2: float, phys2: float):
    if raw1 == raw2:
        print("[ERROR] Raw Point 1 and Raw Point 2 cannot be identical!", file=sys.stderr)
        sys.exit(1)

    slope = (phys2 - phys1) / (raw2 - raw1)
    offset = phys1 - (slope * raw1)

    print("==================================================")
    print("      TWO-POINT LINEAR CALIBRATION RESULTS        ")
    print("==================================================")
    print(f" Point 1: Raw = {raw1:8.2f}  --> Physical = {phys1:6.2f}")
    print(f" Point 2: Raw = {raw2:8.2f}  --> Physical = {phys2:6.2f}")
    print("--------------------------------------------------")
    print(f" Slope (m):      {slope:+.8f}")
    print(f" Intercept (b):  {offset:+.4f}")
    print(f" Formula:        Physical = ({slope:.6f} * raw) + ({offset:.4f})")
    print("==================================================")
    print("\n/* Ready-to-Paste ESP32 Preferences C++ Boilerplate */")
    print(f"const float CALIB_SLOPE  = {slope:.8f}f;")
    print(f"const float CALIB_OFFSET = {offset:.4f}f;")
    print("""
float read_calibrated_sensor(int raw_adc) {
    float val = (CALIB_SLOPE * (float)raw_adc) + CALIB_OFFSET;
    return constrain(val, 0.0f, 100.0f);
}
""")

def compute_tare_scale(tare: float, known_raw: float, known_weight: float):
    if known_raw == tare:
        print("[ERROR] Known raw weight reading equals tare offset!", file=sys.stderr)
        sys.exit(1)

    scale_factor = (known_raw - tare) / known_weight

    print("==================================================")
    print("     TARE & SCALE FACTOR CALIBRATION RESULTS      ")
    print("==================================================")
    print(f" Tare Offset (Empty): {tare:8.2f}")
    print(f" Known Weight Applied: {known_weight:8.2f} units")
    print(f" Raw Reading at Weight: {known_raw:8.2f}")
    print("--------------------------------------------------")
    print(f" Scale Factor:        {scale_factor:8.4f} counts/unit")
    print(f" Formula:             Weight = (raw - {tare:.2f}) / {scale_factor:.4f}")
    print("==================================================")
    print("\n/* Ready-to-Paste C++ Boilerplate */")
    print(f"const float TARE_OFFSET  = {tare:.2f}f;")
    print(f"const float SCALE_FACTOR = {scale_factor:.4f}f;")
    print("""
float read_weight(float raw_count) {
    return (raw_count - TARE_OFFSET) / SCALE_FACTOR;
}
""")

def compute_quadratic_poly(x1: float, y1: float, x2: float, y2: float, x3: float, y3: float):
    denom = (x1 - x2) * (x1 - x3) * (x2 - x3)
    if abs(denom) < 1e-9:
        print("[ERROR] Points cannot share identical X values!", file=sys.stderr)
        sys.exit(1)

    a = (x3 * (y2 - y1) + x2 * (y1 - y3) + x1 * (y3 - y2)) / denom
    b = (x3*x3 * (y1 - y2) + x2*x2 * (y3 - y1) + x1*x1 * (y2 - y3)) / denom
    c = (x2 * x3 * (x2 - x3) * y1 + x3 * x1 * (x3 - x1) * y2 + x1 * x2 * (x1 - x2) * y3) / denom

    print("==================================================")
    print("      3-POINT QUADRATIC CALIBRATION RESULTS       ")
    print("==================================================")
    print(f" P1: ({x1:.2f}, {y1:.2f}) | P2: ({x2:.2f}, {y2:.2f}) | P3: ({x3:.2f}, {y3:.2f})")
    print("--------------------------------------------------")
    print(f" a: {a:+.8f}")
    print(f" b: {b:+.8f}")
    print(f" c: {c:+.8f}")
    print(f" Formula: Physical = ({a:.6f} * raw^2) + ({b:.6f} * raw) + ({c:.4f})")
    print("==================================================")
    print("\n/* Ready-to-Paste C++ Function */")
    print(f"const float CALIB_A = {a:.8f}f;")
    print(f"const float CALIB_B = {b:.8f}f;")
    print(f"const float CALIB_C = {c:.8f}f;")
    print("""
float read_calibrated_poly(float raw) {
    return (CALIB_A * raw * raw) + (CALIB_B * raw) + CALIB_C;
}
""")

def main():
    parser = argparse.ArgumentParser(description="Sensor Calibration Calculator")
    parser.add_argument("--mode", choices=["two-point", "tare-scale", "poly3", "sample", "filter"])
    
    # Live serial sampling arguments
    parser.add_argument("--sample-port", type=str, help="Serial port to sample from (e.g. /dev/ttyACM0)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("--count", type=int, default=20, help="Number of samples to capture")

    # Two-point arguments
    parser.add_argument("--raw1", type=float)
    parser.add_argument("--phys1", type=float)
    parser.add_argument("--raw2", type=float)
    parser.add_argument("--phys2", type=float)

    # Tare scale arguments
    parser.add_argument("--tare", type=float)
    parser.add_argument("--known-raw", type=float)
    parser.add_argument("--known-weight", type=float)

    # 3-point quadratic arguments
    parser.add_argument("--x1", type=float)
    parser.add_argument("--y1", type=float)
    parser.add_argument("--x2", type=float)
    parser.add_argument("--y2", type=float)
    parser.add_argument("--x3", type=float)
    parser.add_argument("--y3", type=float)

    # Sample array argument
    parser.add_argument("--samples", type=str, help="Comma-separated raw readings for filtering")

    args = parser.parse_args()

    # If sampling from serial port directly
    if args.sample_port:
        raw_list = sample_from_serial(args.sample_port, args.baud, args.count)
        mean_val, std_val, filtered = filter_samples(raw_list)
        print(f"[DATA FILTER] Ingested: {len(raw_list)} samples | Valid: {len(filtered)}")
        print(f"              Mean: {mean_val:.2f} | StdDev: {std_val:.2f}")
        return

    if args.samples:
        raw_list = [float(x.strip()) for x in args.samples.split(",") if x.strip()]
        mean_val, std_val, filtered = filter_samples(raw_list)
        print(f"[DATA FILTER] Ingested: {len(raw_list)} samples | Valid: {len(filtered)}")
        print(f"              Mean: {mean_val:.2f} | StdDev: {std_val:.2f}")

    if args.mode == "two-point":
        if None in (args.raw1, args.phys1, args.raw2, args.phys2):
            print("[ERROR] --mode two-point requires --raw1, --phys1, --raw2, --phys2", file=sys.stderr)
            sys.exit(1)
        compute_two_point(args.raw1, args.phys1, args.raw2, args.phys2)

    elif args.mode == "tare-scale":
        if None in (args.tare, args.known_raw, args.known_weight):
            print("[ERROR] --mode tare-scale requires --tare, --known-raw, --known-weight", file=sys.stderr)
            sys.exit(1)
        compute_tare_scale(args.tare, args.known_raw, args.known_weight)

    elif args.mode == "poly3":
        if None in (args.x1, args.y1, args.x2, args.y2, args.x3, args.y3):
            print("[ERROR] --mode poly3 requires --x1, --y1, --x2, --y2, --x3, --y3", file=sys.stderr)
            sys.exit(1)
        compute_quadratic_poly(args.x1, args.y1, args.x2, args.y2, args.x3, args.y3)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
analyze_crash.py - ESP32 Serial Crash & Panic Dump Diagnostic Analyzer
Parses serial output for Guru Meditation errors, Brownout resets, and Watchdog panics.
"""

import sys
import re
import argparse
import time
from pathlib import Path

# Enable importing sibling scripts (serial_monitor)
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from serial_monitor import Paths, running_pid, resolve_port, PortError
except ImportError:
    Paths = None
    running_pid = None
    resolve_port = None
    PortError = RuntimeError

CRASH_PATTERNS = [
    {
        "pattern": r"Brownout detector was triggered",
        "title": "CRITICAL: Hardware Brownout Reset Detected",
        "cause": "The supply voltage dropped below 2.7V during a high-current event (typically Wi-Fi/BLE transmission or relay actuation).",
        "fix": "1. Connect a 47µF - 100µF electrolytic capacitor across 3.3V and GND.\n2. Power board from a powered USB hub or dedicated 5V power supply rather than a passive USB port."
    },
    {
        "pattern": r"Guru Meditation Error.*LoadProhibited",
        "title": "CRITICAL: Null Pointer Dereference (LoadProhibited)",
        "cause": "Firmware attempted to read from an invalid or uninitialized memory address (nullptr).",
        "fix": "1. Verify that sensor/peripheral object was initialized (e.g. `sensor.begin()`) before calling read methods.\n2. Check for null return values on dynamic memory allocations."
    },
    {
        "pattern": r"Guru Meditation Error.*StoreProhibited",
        "title": "CRITICAL: Memory Write Violation (StoreProhibited)",
        "cause": "Firmware attempted to write data to a read-only or invalid memory address (buffer overflow or corrupted pointer).",
        "fix": "1. Check array bounds and string buffer sizes.\n2. Ensure pointers point to valid RAM memory."
    },
    {
        "pattern": r"Task watchdog got triggered",
        "title": "WARNING: FreeRTOS Task Watchdog Reset (CPU Starvation)",
        "cause": "A task executed in a tight loop for >5 seconds without calling `vTaskDelay()` or yielding, starving the FreeRTOS scheduler.",
        "fix": "1. Add `vTaskDelay(pdMS_TO_TICKS(10))` or `yield()` inside all while() and for() loops.\n2. Avoid long blocking calculations on Core 0."
    },
    {
        "pattern": r"Interrupt wdt timeout on CPU",
        "title": "CRITICAL: Interrupt Watchdog Timeout",
        "cause": "An Interrupt Service Routine (ISR) took longer than 300µs or disabled hardware interrupts for too long.",
        "fix": "1. Remove Serial.print(), delays, or heavy processing from inside ISRs.\n2. Set a volatile flag in the ISR and handle data processing inside the main loop."
    },
    {
        "pattern": r"Stack canary watchpoint triggered",
        "title": "CRITICAL: FreeRTOS Stack Overflow",
        "cause": "A FreeRTOS task exceeded its allocated stack space.",
        "fix": "1. Increase stack allocation in `xTaskCreatePinnedToCore` (e.g. from 2048 to 4096 bytes).\n2. Avoid large local array buffers on the stack; use static buffers or heap."
    }
]

def analyze_text(text: str):
    print("==================================================")
    print("      ESP32 CRASH LOG DIAGNOSTIC REPORT           ")
    print("==================================================")
    
    found_issues = 0
    for rule in CRASH_PATTERNS:
        match = re.search(rule["pattern"], text, re.IGNORECASE)
        if match:
            found_issues += 1
            print(f"\n[FOUND #{found_issues}] {rule['title']}")
            print(f" Root Cause:  {rule['cause']}")
            print(f" Recommended Fix:\n{rule['fix']}")
            print("--------------------------------------------------")

    if found_issues == 0:
        print("\n[RESULT] No fatal crash patterns (Panic/Brownout/WDT) found in the log.")
        print("         Firmware appears to be running without kernel exceptions.")
    else:
        print(f"\nTotal Issues Identified: {found_issues}")

def main():
    parser = argparse.ArgumentParser(description="ESP32 Crash Dump Diagnostic Analyzer")
    parser.add_argument("--file", help="Path to serial log file")
    parser.add_argument("--text", help="Direct text of crash log")
    parser.add_argument("--port", help="Sample live from serial port or active monitor (e.g. /dev/ttyACM0 or 'auto')")
    parser.add_argument("--timeout", type=int, default=5, help="Serial capture timeout in seconds")

    args = parser.parse_args()

    content = ""
    target_port = args.port

    # If neither --file nor --text was provided, assume live port inspection
    if not args.file and not args.text and not target_port:
        target_port = "auto"

    if target_port:
        port = target_port
        if resolve_port:
            try:
                port = resolve_port(target_port)
            except Exception:
                port = target_port

        # Check if serial monitor is already active for this port
        paths = Paths(port) if Paths else None
        pid = running_pid(paths) if (paths and running_pid) else None

        if pid is not None and paths and paths.log.exists():
            print(f"[*] Active serial monitor detected on {port} (pid {pid}).")
            print(f"[*] Reading crash logs from shared stream...")
            try:
                with open(paths.log, "r", errors="ignore") as f:
                    all_lines = f.readlines()
                    recent_lines = all_lines[-150:] if len(all_lines) > 150 else all_lines

                if args.timeout > 0:
                    start_time = time.time()
                    initial_pos = paths.log.stat().st_size
                    with open(paths.log, "r", errors="ignore") as f:
                        f.seek(initial_pos)
                        while time.time() - start_time < args.timeout:
                            new_line = f.readline()
                            if new_line:
                                recent_lines.append(new_line)
                            else:
                                time.sleep(0.1)
                content = "".join(recent_lines)
            except Exception as e:
                print(f"[ERROR] Failed reading shared monitor log: {e}", file=sys.stderr)
                sys.exit(1)

        else:
            try:
                import serial
                print(f"[*] Capturing {args.timeout}s of serial logs from {port}...")
                with serial.Serial(port, 115200, timeout=1.0) as ser:
                    start = time.time()
                    lines = []
                    while time.time() - start < args.timeout:
                        l = ser.readline().decode('utf-8', errors='ignore')
                        if l:
                            lines.append(l)
                    content = "".join(lines)
            except Exception as e:
                print(f"[ERROR] Failed to read from {port}: {e}", file=sys.stderr)
                sys.exit(1)

    elif args.file:
        with open(args.file, "r") as f:
            content = f.read()

    elif args.text:
        content = args.text

    analyze_text(content)

if __name__ == "__main__":
    main()


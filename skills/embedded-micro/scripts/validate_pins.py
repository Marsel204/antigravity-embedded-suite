#!/usr/bin/env python3
"""
validate_pins.py - Microcontroller Pin Safety Validator
Checks proposed GPIO assignments against strapping pins, bus lines, and ADC2/Wi-Fi conflicts.
"""

import sys
import argparse

PINS_DB = {
    "esp32": {
        "flash": {6, 7, 8, 9, 10, 11},
        "strapping": {
            0: "Bootloader selector (LOW = Download Mode)",
            2: "Boot mode / On-board LED",
            5: "SDIO timing (Internal pull-up)",
            12: "CRITICAL: Flash voltage selector (MTDI). HIGH sets 1.8V, bricking 3.3V flash!",
            15: "Debug log silence (MTDO)"
        },
        "input_only": {34, 35, 36, 39},
        "adc2": {0, 2, 4, 12, 13, 14, 15, 25, 26, 27},
        "psram": {16, 17}
    },
    "esp32s3": {
        "flash": {26, 27, 28, 29, 30, 31, 32},
        "octal_psram": {33, 34, 35, 36, 37},
        "strapping": {
            0: "Boot mode (LOW = Download mode, requires external pull-up)",
            3: "JTAG / Boot log control",
            45: "CRITICAL: VDD_SPI voltage selector. HIGH sets 1.8V, bricking 3.3V flash!",
            46: "ROM debug message printing control"
        },
        "usb": {19: "Native USB D-", 20: "Native USB D+"},
        "input_only": set(),
        "adc2": {11, 12, 13, 14, 15, 16, 17, 18, 19, 20}
    }
}

def validate_pins(platform: str, pins: list[int], wifi_enabled: bool = False):
    platform = platform.lower().replace("-", "")
    if platform not in PINS_DB:
        print(f"[!] Platform '{platform}' not in pin safety database. Safe checks skipped.")
        return 0

    db = PINS_DB[platform]
    errors = 0
    warnings = 0

    print(f"=== Pin Safety Validation: {platform.upper()} ===")
    for pin in pins:
        # Check SPI Flash
        if pin in db.get("flash", set()):
            print(f"[ERROR] GPIO {pin}: RESERVED for SPI Flash. System will crash or fail to boot!")
            errors += 1
            continue

        # Check Octal PSRAM / Flash
        if pin in db.get("octal_psram", set()):
            print(f"[WARNING] GPIO {pin}: Used by Octal SPI Flash/PSRAM (e.g. 8MB/16MB modules). Avoid if using PSRAM.")
            warnings += 1

        # Check Native USB
        if "usb" in db and pin in db["usb"]:
            print(f"[WARNING] GPIO {pin}: Native USB ({db['usb'][pin]}). Do not use if USB serial/JTAG is enabled.")
            warnings += 1

        # Check Strapping Pins
        if pin in db.get("strapping", {}):
            print(f"[WARNING] GPIO {pin}: Strapping pin! Note: {db['strapping'][pin]}")
            warnings += 1

        # Check Input Only
        if pin in db.get("input_only", set()):
            print(f"[WARNING] GPIO {pin}: Input-only. Cannot be configured as OUTPUT.")
            warnings += 1

        # Check ADC2 with Wi-Fi
        if wifi_enabled and pin in db.get("adc2", set()):
            print(f"[WARNING] GPIO {pin}: Belongs to ADC2. Incompatible with Wi-Fi! Analog readings will be corrupted.")
            warnings += 1

        if errors == 0 and warnings == 0:
            print(f"[OK] GPIO {pin}: Clean and freely usable.")

    print(f"\nResult: {errors} error(s), {warnings} warning(s).")
    return 1 if errors > 0 else 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Microcontroller Pin Safety Validator")
    parser.add_argument("--platform", default="esp32s3", help="Target: esp32, esp32s3")
    parser.add_argument("--pins", required=True, help="Comma-separated GPIO numbers (e.g., 4,19,45)")
    parser.add_argument("--wifi", action="store_true", help="Set if firmware uses Wi-Fi")
    args = parser.parse_args()

    pin_list = [int(p.strip()) for p in args.pins.split(",") if p.strip()]
    sys.exit(validate_pins(args.platform, pin_list, args.wifi))

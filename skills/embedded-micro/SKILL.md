---
name: embedded-micro
description: Build, verify, flash, and monitor microcontrollers (ESP32, Arduino Uno/Nano/Mega, RP2040, STM32) using headless CLI toolchains (arduino-cli, PlatformIO). Activate when developing firmware, testing embedded code, compiling sketches, assigning GPIO pins, or interacting with microcontroller hardware and serial ports.
---

# Microcontroller & Embedded Development Harness

This skill defines the operational protocol for autonomous firmware development, headless compilation, hardware safety validation, flashing, and automatic serial verification across Arduino and ESP32 boards.

---

## 1. On-Demand Hardware References

Load detailed pinout and electrical constraints on demand to keep token consumption minimal:

| Reference File | Trigger / Scope |
| :--- | :--- |
| `references/hardware-safety.md` | Wiring circuits, pulling pins HIGH/LOW, or reading analog signals with Wi-Fi. |
| `references/esp32-s3.md` | Working specifically with ESP32-S3 boards (pin mappings, USB CDC/JTAG, ADC1/2). |
| `references/arduino-boards.md` | Compiling or wiring for Arduino Uno, Nano, Mega 2560, or Raspberry Pi Pico (RP2040). |

---

## 2. Board-Not-Found Decision Policy (CRITICAL)

When scanning for boards (`arduino-cli board list` or `ls /dev/tty*`):

* **IF Task is Coding or Compiling:**
  - **CONTINUE.** Physical hardware is NOT required for code generation or syntax checks.
  - Compile headlessly with `arduino-cli compile --fqbn <target>`.
  - Report compilation sizing and inform user that code is verified and ready to flash whenever the board is connected.

* **IF Task is Flashing (`upload`) or Serial Monitoring (`monitor`):**
  - **HARD STOP.** Break immediately. Do NOT run `upload` or guess random ports (e.g. `/dev/ttyS4`).
  - Run USB diagnostics (`lsusb`, `journalctl -p 0..6 -e -n 25`) to check physical connection.
  - Inform the user of the exact port status, cable requirements, or bootloader steps.

---

## 3. Pre-Flight GPIO Safety Check

Before writing or modifying pin assignments in firmware, run the validation tool to catch hardware traps, flash collisions, and strapping pin failures:

```bash
python3 ~/.gemini/config/skills/embedded-micro/scripts/validate_pins.py --platform <esp32|esp32s3> --pins <comma-separated-gpios> [--wifi]
```

---

## 4. Headless Compilation & Verification

Always verify syntax and firmware binary generation before claiming a task is done. Keep output token-efficient:

```bash
# Compile for ESP32-S3
arduino-cli compile --fqbn esp32:esp32:esp32s3 <sketch-directory> 2>&1 | tail -n 25

# Compile for Arduino Uno
arduino-cli compile --fqbn arduino:avr:uno <sketch-directory> 2>&1 | tail -n 25

# PlatformIO alternative (if platformio.ini exists)
pio run 2>&1 | tail -n 25
```

---

## 5. Serial Monitoring Protocol (`arduino-cli monitor`)

The standard protocol for observing serial output on microcontrollers uses native `arduino-cli monitor`.

### 5A. Direct Terminal Serial Monitor
To monitor serial logs interactively:
```bash
arduino-cli monitor -p <port> -c baudrate=115200
```
*(Exit the monitor at any time using `Ctrl + C`)*.

### 5B. Dedicated Window Launcher (When Requested)
If the user requests to launch the serial monitor in its own desktop window:
```bash
# Uses alacritty, foot, kitty, or xterm
alacritty --title "Serial Monitor (<port>)" -e arduino-cli monitor -p <port> -c baudrate=115200 &
```

### 5C. Port Exclusivity & Pre-Flash Rule (CRITICAL)
Linux enforces exclusive serial device locking (`TIOCEXCL`).
* **Before running `arduino-cli upload`:** Any active `arduino-cli monitor` process or window MUST be stopped (`Ctrl + C` or kill) to prevent `[Errno 16] Device or resource busy`.
* **After upload completes:** Re-launch or restart the monitor.

*(Optional background telemetry helper: `python3 ~/.gemini/config/skills/embedded-micro/scripts/serial_monitor.py` is preserved for headless cooperative multiplexing if needed).*

---

## 6. Mandatory Automated Serial Verification Chain

Whenever firmware is flashed to a physical board, the agent MUST execute this verification pipeline:

### Step 6A: Automated Boot Capture (MANDATORY)
Immediately after flashing succeeds, capture the first 5 seconds of boot output using native `arduino-cli monitor`:
```bash
timeout 5s arduino-cli monitor -p <port> -c baudrate=115200 2>&1 || true
```
*(Or read via Python telemetry script if programmatic stream parsing is needed)*.

### Step 6B: Report Boot & Runtime Logs
Always display the captured boot output directly in chat under:
`### Live Boot & Runtime Verification`
- Verify that the board bootloaded without crashes, WDT resets, or panic dumps.
- Display the initial telemetry/serial lines directly to the user so they see proof of execution without touching a terminal.



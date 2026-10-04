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

## 5. Dedicated User Serial Monitor & Cooperative Flashing

To provide a dedicated terminal serial monitor window for the user without conflicting with firmware flashing (preventing `[Errno 16] Device or resource busy`), use the embedded cooperative serial manager:

### 5A. Launch Dedicated Serial Monitor Window (For User)
When the user asks to open or view the serial monitor, or during interactive debugging:
```bash
python3 ~/.gemini/config/skills/embedded-micro/scripts/serial_monitor.py launch [--baud 115200] [--port /dev/ttyACM0]
```
- Spawns an interactive terminal window (`alacritty`, `foot`, `kitty`, etc.) streaming live microcontroller logs.
- Simultaneously writes clean, timestamped output to `$XDG_RUNTIME_DIR/embedded-micro/<port>.log`.

### 5B. Cooperative Pre/Post Flash Lifecycle
Linux serial ports are exclusive. When flashing while a monitor is active, pause it before flashing and resume immediately after:
```bash
# 1. Release port before upload
python3 ~/.gemini/config/skills/embedded-micro/scripts/serial_monitor.py pause

# 2. Flash firmware
arduino-cli upload -p <port> --fqbn <target> <sketch-directory>

# 3. Resume monitor immediately (re-attaches user's terminal window)
python3 ~/.gemini/config/skills/embedded-micro/scripts/serial_monitor.py resume
```

---

## 6. Mandatory Automated Serial Verification Chain

Whenever firmware is flashed to a physical board, the agent MUST execute this verification pipeline:

### Step 6A: Automated Boot Capture (MANDATORY)
Immediately after flashing succeeds, capture the first 5 seconds of boot output using the cooperative manager:
```bash
python3 ~/.gemini/config/skills/embedded-micro/scripts/serial_monitor.py capture --duration 5 [--baud 115200]
```
*(If the user's GUI monitor window is already active, `capture` safely tails the shared stream without disrupting the port)*.

### Step 6B: Report Boot & Runtime Logs
Always display the captured boot output directly in chat under:
`### Live Boot & Runtime Verification`
- Verify that the board bootloaded without crashes, WDT resets, or panic dumps.
- Display the initial telemetry/serial lines directly to the user so they see proof of execution without touching a terminal.


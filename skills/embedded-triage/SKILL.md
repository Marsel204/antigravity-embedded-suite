---
name: embedded-triage
description: Diagnose malfunctioning embedded systems, isolate hardware vs firmware bugs, decode ESP32 crash dumps and reset reasons, flash in-situ diagnostic probes, and guide interactive hardware-in-the-loop troubleshooting interviews.
---

# Embedded Hardware-in-the-Loop (HIL) Triage Skill

`<skill-dir>` is the directory containing this SKILL.md; sibling skills are at `<skill-dir>/../<name>/`.

This skill defines the operational protocol for isolating bugs, diagnosing unexpected hardware behavior, decoding crash dumps, and guiding interactive physical troubleshooting.

---

## 1. The 4-Phase Fault Isolation State Machine

When a system fails to behave as expected (crashes, reboots, returns -1, freezes, or fails to actuate), execute this pipeline:

### Phase 1: Live Serial Monitor & Crash Inspection
1. **Interactive Serial Monitor:**
   Inspect live reboot loops, panic dumps, and boot logs directly using `arduino-cli monitor`:
   ```bash
   timeout 5s arduino-cli monitor -p <port> -c baudrate=115200
   ```
   *(Only when the user explicitly requests a separate window: `alacritty --title "Triage Monitor" -e arduino-cli monitor -p <port> -c baudrate=115200 &`)*.

2. **Automated Crash Analysis (Optional):**
   Run the crash pattern analyzer against captured output, text, or files:
   ```bash
   python3 <skill-dir>/scripts/analyze_crash.py --port <port> --timeout 5
   ```
   Use `--file crash.log` for saved logs, `--file -` for stdin, or pipe a log with no arguments; non-TTY stdin is read without opening a serial port. Explicit `--port` requests live capture.
   - If a **Guru Meditation**, **Panic Dump**, or **Brownout** is detected, the analyzer immediately identifies the root cause (e.g. Null pointer, Stack overflow, Power sag) without needing hardware changes.

### Phase 2: In-Situ Diagnostic Probe Deployment
If the code compiles and runs but peripherals don't respond (e.g. sensor always returns 0/-1, I2C freeze):
1. **Flash Diagnostic Probe:**
   This probe REPLACES the user’s firmware: confirm firmware-replacement authorization before flashing, including the exact board, FQBN, port, and sketch. It is ESP32-family only because it uses `esp_reset_reason()`. Release the port held by the task-owned monitor; don’t kill unrelated user sessions. Compile before uploading:
   ```bash
   arduino-cli compile --fqbn <fqbn> <skill-dir>/probes/hardware_health_probe
   arduino-cli upload -p <port> --fqbn <fqbn> <skill-dir>/probes/hardware_health_probe
   ```
Set SDA_PIN and SCL_PIN to the confirmed wiring at compile time, for example:
   `--build-property "compiler.cpp.extra_flags=-DSDA_PIN=21 -DSCL_PIN=22"`.
   Arduino CLI documents this property; verify that the selected core's C++ recipe consumes it and preserve any required existing flags. See [compile documentation](https://docs.arduino.cc/arduino-cli/commands-reference/arduino-cli_compile/).
2. **Monitor Probe Telemetry:**
   Launch monitor to read the probe diagnostic report:
   ```bash
   timeout 5s arduino-cli monitor -p <port> -c baudrate=115200
   ```
   - Identifies the last hardware reset reason (`esp_reset_reason()`).
   - Scans all 127 I2C addresses on SDA/SCL lines.

   - Reports free heap, internal chip temperature, and stack health.


### Phase 3: Interactive Physical HIL Interview
If the fault is determined to be physical/electrical, ask the user targeted, single-topic questions (using clear prompts or multiple-choice options):
* **Power Check:** "Does the board reboot at the exact moment Wi-Fi connects or the relay clicks? (Indicates USB brownout / power sag)."
* **Ground Check:** "Is there a common Ground wire connecting the external 5V/12V supply to the ESP32 GND?"
* **Wiring Check:** "Are the SDA and SCL wires plugged into the exact pins assigned in the firmware?"

### Phase 4: Root Cause Remediation
Apply the fix based on the triage conclusion:
* **Firmware Fix:** Patch code, add `vTaskDelay()` to prevent WDT timeout, adjust I2C address, or fix null pointer.
* **Electrical Fix:** Provide exact instructions to add decoupling capacitors, insert level shifters, or fix loose jumper wires.

---

## 2. On-Demand References

| Reference File | Purpose / Scope |
| :--- | :--- |
| `references/diagnostic-trees.md` | Symptom-to-cause isolation trees for Brownouts, I2C lockups, Floating inputs, and WDT resets. |
| `references/esp32-reset-reasons.md` | Comprehensive decoder for all `esp_reset_reason()` enum codes. |

---

## 3. Collaboration with Other Skills
* Uses `embedded-micro` to flash diagnostic probes and production patches.
* Uses `kicad-schematic` to verify and redraw the correct wiring if breadboard connections were wrong.

Agent-run captures are bounded. Exit 124 means the capture window ended; any other nonzero exit is a real port/tool failure to report. A timeout alone does not establish runtime correctness.

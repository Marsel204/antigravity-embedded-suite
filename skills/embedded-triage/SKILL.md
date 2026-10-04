---
name: embedded-triage
description: Diagnose malfunctioning embedded systems, isolate hardware vs firmware bugs, decode ESP32 crash dumps and reset reasons, flash in-situ diagnostic probes, and guide interactive hardware-in-the-loop troubleshooting interviews.
---

# Embedded Hardware-in-the-Loop (HIL) Triage Skill

This skill defines the operational protocol for isolating bugs, diagnosing unexpected hardware behavior, decoding crash dumps, and guiding interactive physical troubleshooting.

---

## 1. The 4-Phase Fault Isolation State Machine

When a system fails to behave as expected (crashes, reboots, returns -1, freezes, or fails to actuate), execute this pipeline:

### Phase 1: Live Serial Monitor & Crash Inspection
1. **Launch Dedicated Monitor Window (For User):**
   When troubleshooting or when requested by the user, launch a live floating serial terminal:
   ```bash
   python3 ~/.gemini/config/skills/embedded-triage/scripts/serial_monitor.py launch [--baud 115200] [--port /dev/ttyACM0]
   ```
2. **Run Automated Crash Analyzer:**
   ```bash
   python3 ~/.gemini/config/skills/embedded-triage/scripts/analyze_crash.py [--port auto] [--timeout 5]
   ```
   - Automatically detects if the monitor window is running and inspects the shared stream without port lock contention.
   - If a **Guru Meditation**, **Panic Dump**, or **Brownout** is detected, the analyzer immediately identifies the root cause (e.g. Null pointer, Stack overflow, Power sag) without needing hardware changes.

### Phase 2: In-Situ Diagnostic Probe Deployment
If the code compiles and runs but peripherals don't respond (e.g. sensor always returns 0/-1, I2C freeze):
1. Flash the universal diagnostic probe cooperatively:
   ```bash
   # 1. Release serial port before upload (monitor window stays open)
   python3 ~/.gemini/config/skills/embedded-triage/scripts/serial_monitor.py pause

   # 2. Compile & upload diagnostic probe
   arduino-cli compile --fqbn esp32:esp32:esp32s3 ~/.gemini/config/skills/embedded-triage/probes
   arduino-cli upload -p /dev/ttyACM0 --fqbn esp32:esp32:esp32s3 ~/.gemini/config/skills/embedded-triage/probes

   # 3. Re-attach serial monitor window
   python3 ~/.gemini/config/skills/embedded-triage/scripts/serial_monitor.py resume
   ```
2. Automatically monitor the probe output:
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

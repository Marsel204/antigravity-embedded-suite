---
name: sensor-calibration
description: Guide interactive sensor calibration experiments, sample raw ADC/sensor values over serial, calculate mathematical slopes/offsets, and persist calibration to ESP32 NVS or EEPROM. Activate when calibrating sensors (soil moisture, load cells, thermistors, turbidity, pH, IMU, gas), taring scales, or doing experimental calibration.
---

# Sensor Calibration & Interactive Experimentation Skill

This skill defines the operational protocol for Human-in-the-Loop hardware calibration, statistical serial sampling, mathematical curve fitting, and non-volatile parameter persistence tailored to specific sensor physics.

---

## 1. The 6-Phase Sensor-Specific Calibration Protocol

### Phase 0: Sensor Identification & Protocol Lookup (MANDATORY)
Identify the exact sensor model and load its dedicated calibration protocol from `references/sensor-catalog.md`:
* **Soil Moisture:** 2-Point Air (0%) vs Water (100%) inverted linear fit.
* **Load Cells (HX711):** Tare (0g) vs Known Calibration Weight (Scale Factor).
* **pH Probes:** Dual-buffer immersion (pH 7.00 neutral zero + pH 4.01 acidic slope).
* **Turbidity Sensors:** Clear water (0 NTU) vs opaque reference (Quadratic fit).
* **IMU (MPU6050/BNO055):** Still-table zero-rate drift + 1g gravity orientation.
* **Gas Sensors (MQ Series):** Heater burn-in + clean air baseline resistance ($R_0$).

### Phase 1: Deploy Raw Sampler Firmware
Flash a lightweight sketch via `embedded-micro` that reads the raw ADC/register value and prints it formatted as:
`RAW: <integer_value>` every 100ms at 115200 baud.
*(If a serial monitor window is active, pause it before upload and resume immediately after)*.

### Phase 2: Launch Dedicated Serial Monitor & Issue Step Prompts
1. **Launch Live Monitor Window (For User):**
   Open a dedicated floating terminal window so the user can watch raw readings stabilize:
   ```bash
   python3 ~/.gemini/config/skills/sensor-calibration/scripts/serial_monitor.py launch [--baud 115200] [--port /dev/ttyACM0]
   ```
2. **Issue Physical Step Prompt:**
   Provide tailored physical instructions matching the sensor's physical medium and wait for user confirmation:
   - *Example (pH Probe):* "Step 1: Rinse probe in distilled water and submerge in pH 7.00 buffer solution. Watch the serial monitor until RAW values stabilize, then type 'ready'."
   - *Example (Load Cell):* "Step 1: Remove all items from the scale platform (Tare state). Type 'ready' when stable."

### Phase 3: Automated Bounded Serial Data Harvesting
The instant the user says "ready", capture 20 raw samples in the background:
```bash
python3 ~/.gemini/config/skills/sensor-calibration/scripts/compute_calibration.py --sample-port /dev/ttyACM0 --count 20
```
- Automatically reads from the active monitor's shared log without port conflict, or connects directly if no window is open.
- Computes mean and standard deviation. Discards samples with high variance (noise/movement).

### Phase 4: Multi-Point Testing & Mathematical Fit
Prompt for subsequent reference states (e.g. pH 4.01 buffer, or known test weight) and compute the exact mathematical model:
```bash
python3 ~/.gemini/config/skills/sensor-calibration/scripts/compute_calibration.py \
  --mode <two-point|tare-scale|poly3> [arguments...]
```

### Phase 5: Deploy Production Firmware with NVS Flash Persistence
1. Release serial port before flashing:
   ```bash
   python3 ~/.gemini/config/skills/sensor-calibration/scripts/serial_monitor.py pause
   ```
2. Generate and flash production firmware using ESP32 `Preferences.h` (or Arduino `EEPROM.h`) that stores the calculated parameters directly into flash memory.
3. Resume monitor:
   ```bash
   python3 ~/.gemini/config/skills/sensor-calibration/scripts/serial_monitor.py resume
   ```


---

## 2. On-Demand References

| Reference File | Purpose / Scope |
| :--- | :--- |
| `references/sensor-catalog.md` | Sensor-by-sensor physical protocols: Soil, Load Cells, pH, Turbidity, IMU, Gas. |
| `references/calibration-models.md` | Mathematical formulas: 2-point linear, tare/scale, Steinhart-Hart, polynomial fit. |
| `references/nvs-persistence.md` | Boilerplate code for saving and loading calibration floats using `Preferences.h` / `EEPROM.h`. |

---

## 3. Handshake with `embedded-micro`
* Use `embedded-micro` to compile and upload the raw sampler sketch in Phase 1.
* Use `embedded-micro` to flash the final production firmware in Phase 5.

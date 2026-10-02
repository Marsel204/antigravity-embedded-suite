# Antigravity Embedded Engineering Suite

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Microcontroller: ESP32 & Arduino](https://img.shields.io/badge/Platform-ESP32%20%7C%20Arduino%20%7C%20RP2040-blue.svg)](https://espressif.com)
[![Harness: Antigravity](https://img.shields.io/badge/Agent%20Harness-Antigravity%20%2F%20Claude%20Code-purple.svg)](https://github.com)

The **Antigravity Embedded Engineering Suite** is a 4-pillar agentic development framework for microcontrollers (ESP32, ESP32-S3, ESP32-C3, Arduino Uno/Nano/Mega, RP2040). It equips AI coding assistants with end-to-end hardware intelligence—from electrical schematic design to headless compilation, automated flashing, sensor calibration, and crash triage.

---

## The 4 Pillars

```
   1. Circuit & CAD               2. Firmware & Flash            3. Calibration & Math          4. Debugging & Triage
 ┌──────────────────────┐       ┌──────────────────────┐       ┌──────────────────────┐       ┌──────────────────────┐
 │   /kicad-schematic   │ ────► │   /embedded-micro    │ ────► │ /sensor-calibration  │ ────► │   /embedded-triage   │
 ├──────────────────────┤       ├──────────────────────┤       ├──────────────────────┤       ├──────────────────────┤
 │ • Breadboard table   │       │ • Pin safety checks  │       │ • Guided experiments │       │ • Crash log decoding │
 │ • Level shifters/R/C │       │ • Headless compile   │       │ • Raw serial sample  │       │ • In-situ I2C probe  │
 │ • Native .kicad_sch  │       │ • Auto USB flashing  │       │ • Outlier rejection  │       │ • Reset reason decode│
 │ • Auto visual SVG    │       │ • Auto serial monitor│       │ • Save to NVS Flash  │       │ • Guided HIL Q&A     │
 └──────────────────────┘       └──────────────────────┘       └──────────────────────┘       └──────────────────────┘
```

### 1. `kicad-schematic` (Hardware Circuit Design)
* **Visual Schematic:** Automatically generates vector SVG schematics and Mermaid circuit diagrams.
* **Desk Breadboard Guide:** Instant pin-to-pin hookup table with polarities and passive component sizing.
* **Native KiCad CAD:** Synthesizes S-expression `.kicad_sch` files compatible with KiCad 7, 8, and 9.
* **Electrical Safety:** Enforces 3.3V vs 5.0V level translation, I2C pull-ups, and decoupling capacitors.

### 2. `embedded-micro` (Firmware Build & Flash)
* **Pre-Flight Pin Validation:** Prevents strapping pin traps (GPIO 12/45 voltage trap, GPIO 0 bootloader) and flash bus collisions.
* **Headless Compilation:** Compiles Arduino C++ and FreeRTOS firmware headlessly via `arduino-cli` with zero guesswork.
* **Automated Post-Flash Verification:** Flashes over USB serial and automatically monitors the initial boot cycle to confirm live execution in chat.

### 3. `sensor-calibration` (Human-in-the-Loop Experimentation)
* **Sensor Catalog:** Tailored protocols for Soil Moisture, Load Cells (HX711), pH Probes, Turbidity, IMUs, and Gas Sensors.
* **Statistical Data Sampling:** Background USB serial sampling with outlier rejection ($2\sigma$ filter).
* **Curve Fitting Math:** Solves 2-point linear ($y=mx+b$), tare/scale factor, and 3-point quadratic polynomial equations.
* **NVS Flash Persistence:** Stores calibration parameters into non-volatile flash memory (`Preferences.h` / `EEPROM.h`).

### 4. `embedded-triage` (Hardware Detective & Debugger)
* **Crash Dump Decoding:** Translates cryptic Guru Meditation errors, LoadProhibited exceptions, and brownouts into plain English.
* **In-Situ Diagnostic Probe:** All-in-one probe sketch that queries `esp_reset_reason()` and scans all 127 I2C bus addresses.
* **Interactive HIL Interview:** Guides the human developer through physical checks (common ground, power sag, loose jumpers).

---

## Directory Structure

```text
antigravity-embedded-suite/
├── README.md
├── LICENSE
├── .gitignore
├── rules/
│   └── embedded-rules.md             # Universal agent guardrails
└── skills/
    ├── embedded-micro/               # Firmware build, flash & monitor
    │   ├── SKILL.md
    │   ├── references/               # Board profiles (S3, Arduino) & safety
    │   └── scripts/                  # Pin validator
    ├── kicad-schematic/              # Circuit design & KiCad CAD
    │   ├── SKILL.md
    │   ├── references/               # Design rules & S-expression specs
    │   └── scripts/                  # Schematic & SVG generators
    ├── sensor-calibration/           # Guided experiments & math
    │   ├── SKILL.md
    │   ├── references/               # Sensor catalog & NVS storage
    │   └── scripts/                  # Sampling & curve fitting
    └── embedded-triage/              # Fault isolation & crash decoder
        ├── SKILL.md
        ├── probes/                   # In-situ I2C & reset probe sketch
        ├── references/               # Diagnostic trees & reset reasons
        └── scripts/                  # Crash dump analyzer
```

---

## Installation

### For Antigravity
Copy the skills and rules into your local Antigravity configuration directory:
```bash
cp -r skills/* ~/.gemini/config/skills/
cp -r rules/* ~/.gemini/config/rules/
```

### For Claude Code
Copy into your Claude skills directory:
```bash
cp -r skills/* ~/.claude/skills/
```

---

## License
MIT License. Created for the Antigravity developer community.

---
name: kicad-schematic
description: Design circuit schematics, breadboard wiring tables, and native KiCad (.kicad_sch) files. Activate when designing circuits, connecting sensors/modules to microcontrollers, calculating pull-up resistors or level shifters, or generating KiCad schematics and netlists.
---

# KiCad & Circuit Schematic Design Skill

This skill defines the operational protocol for hardware circuit design, automated visual schematic rendering, breadboard wiring generation, and KiCad schematic synthesis.

---

## 1. Mandatory 3-Deliverable Protocol

Every circuit design task MUST automatically produce and display three coordinated deliverables:

### Deliverable 1: Visual Schematic Display (AUTOMATIC INLINE SVG)
Always generate and directly embed the visual vector schematic diagram so the user sees the circuit immediately:
1. Synthesize the SVG:
   ```bash
   python3 ~/.gemini/config/skills/kicad-schematic/scripts/generate_circuit_svg.py --input <circuit-spec.json> --output <scratch_dir>/schematic.svg
   ```
2. Copy or save the SVG into the active artifact directory (`<appDataDir>/brain/<conversation-id>/schematic.svg`).
3. Embed it directly in chat using Markdown image syntax:
   `![Circuit Schematic](/absolute/path/to/schematic.svg)`
4. Accompany it with an inline GitHub-flavored `mermaid` circuit diagram.

### Deliverable 2: Desk Breadboard Wiring Guide (Markdown Table)
A clean, unmistakable pin-to-pin wiring table showing:
- Exact jumper connections (From MCU Pin -> Component Pin).
- Polarity warnings (Anode/Cathode, VCC/GND).
- Passive component specifications (e.g. 220Ω resistor, 4.7kΩ I2C pull-ups).
- 3.3V vs 5.0V voltage warnings.

### Deliverable 3: Native KiCad Schematic (`.kicad_sch`)
Generate the KiCad CAD schematic using the S-expression generator:
```bash
python3 ~/.gemini/config/skills/kicad-schematic/scripts/generate_kicad_sch.py --input <circuit-spec.json> --output <scratch_dir>/<name>.kicad_sch
```
Provide a direct clickable link to the `.kicad_sch` file.

---

## 2. Electrical Safety & Pre-Flight Checks

Before generating wiring or schematics, verify these electrical constraints:

1. **Logic Level Mismatch:**
   - **Never connect 5V logic directly to 3.3V microcontrollers (ESP32, RP2040, STM32).**
   - For bidirectional lines (I2C): Use BSS138/TXS0108E MOSFET-based level shifter.
   - For unidirectional inputs (5V Sensor TX -> 3.3V MCU RX): Use a resistor divider (1kΩ / 2kΩ) or level shifter.

2. **I2C Bus Pull-Ups:**
   - Always ensure SDA and SCL have pull-up resistors to the **3.3V rail** (typically 4.7kΩ for 100/400 kHz).

3. **Decoupling Capacitors:**
   - Every active sensor/IC must have a 100nF (0.1µF) ceramic capacitor across VCC and GND placed as close to the IC pins as possible.

4. **Inductive Loads (Relays, Solenoids, Motors):**
   - Never drive directly from an MCU GPIO (max 12–20mA). Use an NPN transistor, MOSFET, or optocoupler.
   - Always place a reverse-biased flyback diode (1N4007 or 1N4148) across the inductive coil.

---

## 3. On-Demand References

| Reference | Purpose |
| :--- | :--- |
| `references/circuit-design-rules.md` | In-depth formulas for level shifters, pull-ups, voltage dividers, and current calculations. |
| `references/kicad-sexpr.md` | Syntax guide and S-expression format reference for KiCad 7/8/9 schematics. |

---

## 4. Handshake with `embedded-micro`

Once the circuit is designed and wiring is confirmed, pass the pin assignments directly into the firmware workflow:
1. Verify selected pins using `embedded-micro`'s validator:
   ```bash
   python3 ~/.gemini/config/skills/embedded-micro/scripts/validate_pins.py --platform <mcu> --pins <pins>
   ```
2. Write and compile the firmware code referencing the exact pin names established in the schematic.

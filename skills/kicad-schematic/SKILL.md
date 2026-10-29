---
name: kicad-schematic
description: Design circuit schematics, breadboard wiring tables, and native KiCad (.kicad_sch) files. Activate when designing circuits, connecting sensors/modules to microcontrollers, calculating pull-up resistors or level shifters, or generating KiCad schematics and netlists.
---

# KiCad & Circuit Schematic Design Skill

`<skill-dir>` is the directory containing this SKILL.md; sibling skills are at `<skill-dir>/../<name>/`.

This skill defines the operational protocol for hardware circuit design, automated visual schematic rendering, breadboard wiring generation, and KiCad schematic synthesis.

---

## 1. Mandatory 3-Deliverable Protocol

When the user asks for a schematic, KiCad artifact, or wiring design, produce the three coordinated deliverables below, clearly identifying draft generator output. For narrow questions (for example, I2C pull-up sizing on an Uno), answer directly with the calculation; do not generate three artifacts.

### Deliverable 1: Visual Schematic Display (AUTOMATIC INLINE SVG)
Always generate and directly embed the visual vector schematic diagram so the user sees the circuit immediately:
1. Synthesize the SVG:
   ```bash
   python3 <skill-dir>/scripts/generate_circuit_svg.py --input <circuit-spec.json> --output <scratch_dir>/schematic.svg
   ```
2. Save the SVG in the harness-designated output directory (or a scratch directory).
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
python3 <skill-dir>/scripts/generate_kicad_sch.py --input <circuit-spec.json> --output <scratch_dir>/<name>.kicad_sch
```
Provide a direct clickable link to the `.kicad_sch` file.

---

## 2. Electrical Safety & Pre-Flight Checks

Before generating wiring or schematics, verify these electrical constraints:

1. **Logic Level Mismatch:**
   - **Never connect 5V logic directly to 3.3V microcontrollers (ESP32, RP2040, STM32).**
   - For bidirectional lines (I2C): Use BSS138/PCA9306-style bidirectional level shifter.
   - For unidirectional inputs (5V Sensor TX -> 3.3V MCU RX): Use a resistor divider (1kΩ / 2kΩ) or level shifter.

2. **I2C Bus Pull-Ups:**
   - Pull SDA/SCL up to a bus voltage tolerated by every device, also satisfying every input's HIGH threshold. A 5V AVR Uno has VIH minimum 0.7×VCC = 3.5V; with 3.3V-only sensors use a BSS138/PCA9306-style bidirectional level shifter and pull-ups on each side.
   - Size resistors from bus capacitance and allowed rise time: Rmax = tr / (0.8473 × Cbus), also checking sink-current limits. Typical starting values are 4.7kΩ at 100kHz and 2.2kΩ at 400kHz, subject to those checks. Many breakout boards already include pull-ups; account for their parallel resistance.

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
   python3 <skill-dir>/../embedded-micro/scripts/validate_pins.py --platform <mcu> --pins <pins>
   ```
2. Write and compile the firmware code referencing the exact pin names established in the schematic.

## 5. Circuit-Spec JSON & Generator Limits

Both generators accept a JSON object with `title`, a `components` array, and a `nets` array:
```json
{
  "title": "LED prototype",
  "components": [
    {"ref": "U1", "value": "ESP32", "lib_id": "Connector:Conn_01x04_Pin"},
    {"ref": "R1", "value": "220 ohm", "lib_id": "Device:R"}
  ],
  "nets": [{"name": "GPIO4"}]
}
```
The SVG renderer reads title and component ref/value (the first component is the MCU), but ignores nets entirely and draws an illustrative series layout. The KiCad generator reads component ref/value/lib_id and net name; endpoint/node fields and additional fields are ignored. Defaults apply to missing fields; this is not a connectivity schema.

The .kicad_sch output has no wires or embedded symbol definitions: its exported netlist is empty and ERC flags dangling labels. Present it as a starting skeleton, never as a verified schematic. For complete designs, supply correct connected symbols and wiring independently of these helpers. If `kicad-cli` is available, run `kicad-cli sch erc --output <scratch_dir>/erc.rpt <scratch_dir>/<name>.kicad_sch` and report the actual result. Otherwise disclose that ERC was not run. Parenthesis balance does not establish electrical correctness.

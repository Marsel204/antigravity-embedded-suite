#!/usr/bin/env python3
"""
generate_circuit_svg.py - Automatic Circuit Schematic SVG Renderer
Generates a visual SVG circuit diagram from JSON circuit specs for direct display in markdown/chat.
"""

import sys
import json
import argparse

def generate_svg(circuit_data: dict) -> str:
    title = circuit_data.get("title", "Circuit Schematic")
    components = circuit_data.get("components", [])
    nets = circuit_data.get("nets", [])

    svg_width = max(760, 220 + len(components) * 160)
    svg_height = 340

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}" width="100%" height="100%" style="background:#0f172a; font-family: ui-monospace, monospace, sans-serif;">')
    lines.append('  <defs>')
    lines.append('    <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">')
    lines.append('      <path d="M 0 0 L 10 5 L 0 10 z" fill="#f59e0b"/>')
    lines.append('    </marker>')
    lines.append('  </defs>')

    # Title Banner
    lines.append(f'  <text x="30" y="38" fill="#f8fafc" font-size="16" font-weight="bold">{title}</text>')
    lines.append('  <text x="30" y="58" fill="#94a3b8" font-size="11">Generated via kicad-schematic | Antigravity Embedded</text>')

    # MCU Block (Left)
    mcu = components[0] if components else {"ref": "U1", "value": "Microcontroller"}
    lines.append('  <!-- MCU Block -->')
    lines.append('  <rect x="40" y="85" width="170" height="200" rx="8" fill="#1e293b" stroke="#38bdf8" stroke-width="2"/>')
    lines.append(f'  <text x="125" y="120" fill="#38bdf8" font-size="14" font-weight="bold" text-anchor="middle">{mcu.get("ref", "U1")}</text>')
    lines.append(f'  <text x="125" y="138" fill="#94a3b8" font-size="11" text-anchor="middle">{mcu.get("value", "MCU")}</text>')

    # Pins on MCU
    lines.append('  <rect x="170" y="160" width="40" height="24" fill="#334155"/>')
    lines.append('  <text x="180" y="176" fill="#f8fafc" font-size="10" font-weight="bold">OUT</text>')
    lines.append('  <line x1="210" y1="172" x2="270" y2="172" stroke="#38bdf8" stroke-width="2"/>')

    lines.append('  <rect x="170" y="235" width="40" height="24" fill="#334155"/>')
    lines.append('  <text x="180" y="251" fill="#f8fafc" font-size="10" font-weight="bold">GND</text>')
    lines.append(f'  <line x1="210" y1="247" x2="{svg_width - 80}" y2="247" stroke="#64748b" stroke-width="2"/>')

    # Draw additional components
    start_x = 270
    comp_spacing = 150
    curr_x = start_x

    for idx, comp in enumerate(components[1:], start=2):
        ref = comp.get("ref", f"C{idx}")
        val = comp.get("value", "")

        # Resistor
        if ref.startswith("R") or "ohm" in val.lower() or "resistor" in val.lower():
            lines.append(f'  <!-- Resistor {ref} -->')
            lines.append(f'  <text x="{curr_x + 45}" y="145" fill="#38bdf8" font-size="12" font-weight="bold" text-anchor="middle">{ref} ({val})</text>')
            lines.append(f'  <polyline points="{curr_x},172 {curr_x+10},172 {curr_x+15},160 {curr_x+25},184 {curr_x+35},160 {curr_x+45},184 {curr_x+55},160 {curr_x+65},184 {curr_x+75},160 {curr_x+80},172 {curr_x+90},172" fill="none" stroke="#f8fafc" stroke-width="2.5" stroke-linejoin="round"/>')
            curr_x += 90
            lines.append(f'  <line x1="{curr_x}" y1="172" x2="{curr_x + 50}" y2="172" stroke="#38bdf8" stroke-width="2"/>')
            curr_x += 50

        # LED / Diode
        elif ref.startswith("D") or "led" in val.lower():
            lines.append(f'  <!-- LED {ref} -->')
            lines.append(f'  <text x="{curr_x + 30}" y="130" fill="#ef4444" font-size="12" font-weight="bold" text-anchor="middle">{ref} ({val})</text>')
            lines.append(f'  <polygon points="{curr_x},152 {curr_x},192 {curr_x+35},172" fill="#ef4444" stroke="#f8fafc" stroke-width="2"/>')
            lines.append(f'  <line x1="{curr_x+35}" y1="152" x2="{curr_x+35}" y2="192" stroke="#f8fafc" stroke-width="3"/>')
            lines.append(f'  <line x1="{curr_x+25}" y1="148" x2="{curr_x+45}" y2="128" stroke="#f59e0b" stroke-width="2" marker-end="url(#arrow)"/>')
            lines.append(f'  <line x1="{curr_x+35}" y1="153" x2="{curr_x+55}" y2="133" stroke="#f59e0b" stroke-width="2" marker-end="url(#arrow)"/>')
            curr_x += 35
            lines.append(f'  <line x1="{curr_x}" y1="172" x2="{curr_x + 60}" y2="172" stroke="#38bdf8" stroke-width="2"/>')
            curr_x += 60

        # Generic IC / Sensor Box
        else:
            lines.append(f'  <!-- Module {ref} -->')
            lines.append(f'  <rect x="{curr_x}" y="125" width="100" height="90" rx="6" fill="#1e293b" stroke="#a855f7" stroke-width="2"/>')
            lines.append(f'  <text x="{curr_x + 50}" y="155" fill="#a855f7" font-size="12" font-weight="bold" text-anchor="middle">{ref}</text>')
            lines.append(f'  <text x="{curr_x + 50}" y="175" fill="#94a3b8" font-size="10" text-anchor="middle">{val}</text>')
            curr_x += 100
            lines.append(f'  <line x1="{curr_x}" y1="172" x2="{curr_x + 40}" y2="172" stroke="#38bdf8" stroke-width="2"/>')
            curr_x += 40

    # Ground Return
    gnd_x = max(curr_x, svg_width - 80)
    lines.append(f'  <!-- Ground Bus Return -->')
    lines.append(f'  <line x1="{curr_x}" y1="172" x2="{gnd_x}" y2="172" stroke="#38bdf8" stroke-width="2"/>')
    lines.append(f'  <line x1="{gnd_x}" y1="172" x2="{gnd_x}" y2="247" stroke="#38bdf8" stroke-width="2"/>')
    lines.append(f'  <circle cx="{gnd_x}" cy="247" r="4" fill="#38bdf8"/>')
    lines.append(f'  <text x="{gnd_x}" y="275" fill="#94a3b8" font-size="11" text-anchor="middle">GND</text>')
    lines.append(f'  <line x1="{gnd_x - 15}" y1="285" x2="{gnd_x + 15}" y2="285" stroke="#64748b" stroke-width="2"/>')
    lines.append(f'  <line x1="{gnd_x - 10}" y1="290" x2="{gnd_x + 10}" y2="290" stroke="#64748b" stroke-width="2"/>')
    lines.append(f'  <line x1="{gnd_x - 5}" y1="295" x2="{gnd_x + 5}" y2="295" stroke="#64748b" stroke-width="2"/>')

    lines.append('</svg>')
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Generate Visual Circuit Schematic SVG from JSON spec")
    parser.add_argument("--input", required=True, help="Input JSON circuit specification file")
    parser.add_argument("--output", required=True, help="Output .svg file")
    args = parser.parse_args()

    with open(args.input, "r") as f:
        circuit_data = json.load(f)

    svg_content = generate_svg(circuit_data)

    with open(args.output, "w") as f:
        f.write(svg_content)

    print(f"[OK] Visual circuit schematic generated: {args.output}")

if __name__ == "__main__":
    main()

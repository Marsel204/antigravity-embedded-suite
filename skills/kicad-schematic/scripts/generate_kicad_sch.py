#!/usr/bin/env python3
"""
generate_kicad_sch.py - Native KiCad 7/8/9 Schematic Generator
Synthesizes valid .kicad_sch files from JSON circuit specifications.
"""

import sys
import json
import uuid
import argparse

def create_uuid():
    return str(uuid.uuid4())

def generate_schematic(circuit_data: dict) -> str:
    title = circuit_data.get("title", "Hardware Prototype Schematic")
    components = circuit_data.get("components", [])
    nets = circuit_data.get("nets", [])

    lines = []
    lines.append('(kicad_sch (version 20231120) (generator "antigravity_kicad_generator")')
    lines.append(f'  (uuid "{create_uuid()}")')
    lines.append('  (paper "A4")')
    lines.append('  (title_block')
    lines.append(f'    (title "{title}")')
    lines.append('    (company "Antigravity Hardware Design")')
    lines.append('    (comment 1 "Generated via kicad-schematic skill")')
    lines.append('  )')
    lines.append('')

    # Component symbols placement
    base_x = 50.8
    base_y = 63.5
    for idx, comp in enumerate(components):
        ref = comp.get("ref", f"U{idx+1}")
        val = comp.get("value", "Generic_Module")
        lib = comp.get("lib_id", "Connector:Conn_01x04_Pin")
        pos_x = base_x + (idx * 50.8)
        pos_y = base_y

        lines.append(f'  (symbol (lib_id "{lib}") (at {pos_x:.2f} {pos_y:.2f} 0) (unit 1)')
        lines.append('    (in_bom yes) (on_board yes) (dnp no)')
        lines.append(f'    (uuid "{create_uuid()}")')
        lines.append(f'    (property "Reference" "{ref}" (at {pos_x:.2f} {pos_y - 5.0:.2f} 0)')
        lines.append('      (effects (font (size 1.27 1.27)))')
        lines.append('    )')
        lines.append(f'    (property "Value" "{val}" (at {pos_x:.2f} {pos_y + 5.0:.2f} 0)')
        lines.append('      (effects (font (size 1.27 1.27)))')
        lines.append('    )')
        lines.append('  )')
        lines.append('')

    # Net labels and interconnects
    net_y = base_y + 35.0
    for idx, net in enumerate(nets):
        net_name = net.get("name", f"NET_{idx+1}")
        pos_x = base_x + (idx * 25.4)
        lines.append(f'  (global_label "{net_name}" (shape bidirectional) (at {pos_x:.2f} {net_y:.2f} 0) (fields_autoplaced)')
        lines.append('    (effects (font (size 1.27 1.27)) (justify left))')
        lines.append(f'    (uuid "{create_uuid()}")')
        lines.append('  )')

    lines.append(')')
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Generate KiCad 7/8/9 .kicad_sch file from JSON spec")
    parser.add_argument("--input", required=True, help="Input JSON circuit specification file")
    parser.add_argument("--output", required=True, help="Output .kicad_sch file")
    args = parser.parse_args()

    with open(args.input, "r") as f:
        circuit_data = json.load(f)

    sch_content = generate_schematic(circuit_data)

    with open(args.output, "w") as f:
        f.write(sch_content)

    # Basic parenthesis balance test
    open_count = sch_content.count("(")
    close_count = sch_content.count(")")
    if open_count != close_count:
        print(f"[ERROR] S-expression parenthesis mismatch! (={open_count}, )={close_count}", file=sys.stderr)
        sys.exit(1)

    print(f"[OK] Successfully synthesized KiCad schematic: {args.output}")
    print(f"     Title: {circuit_data.get('title', 'Untitled')}")
    print(f"     Components: {len(circuit_data.get('components', []))}")
    print(f"     Nets: {len(circuit_data.get('nets', []))}")
    print(f"     Format: KiCad S-Expression (Version 20231120)")

if __name__ == "__main__":
    main()

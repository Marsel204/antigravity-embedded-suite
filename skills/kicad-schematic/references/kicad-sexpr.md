# KiCad Schematic S-Expression Format Guide

KiCad 6, 7, 8, and 9 use human-readable S-expressions for schematic files (`.kicad_sch`).

---

## 1. Minimal Header Structure

A standard `.kicad_sch` file begins with the root `(kicad_sch ...)` element:

```lisp
(kicad_sch (version 20231120) (generator "antigravity_kicad_generator")
  (uuid "d6e3f220-7f28-4c8d-b0a1-778844aa1100")
  (paper "A4")
  (title_block
    (title "ESP32-S3 Hardware Prototype")
    (company "Antigravity Engineering")
    (comment 1 "Generated via kicad-schematic skill")
  )
)
```

---

## 2. Global Labels & Net Wires

Wires and connection labels connect symbols without routing long visible lines:

```lisp
  (wire (pts (xy 50.8 63.5) (xy 63.5 63.5))
    (stroke (width 0) (type default))
    (uuid "5644781e-bb6e-4ad2-a312-6fbe147f8910")
  )

  (global_label "I2C_SDA" (shape input) (at 63.5 63.5 0) (fields_autoplaced)
    (effects (font (size 1.27 1.27)) (justify left))
    (uuid "442e312a-4f51-419b-b0b3-9cc2da318f77")
  )
```

---

## 3. Power Ports (VCC, 3V3, GND)

Power symbols are special library symbols that create global nets automatically:

```lisp
  (symbol (lib_id "power:+3V3") (at 76.2 50.8 0) (unit 1)
    (in_bom yes) (on_board yes) (dnp no)
    (uuid "00000000-0000-0000-0000-000063f11201")
    (property "Reference" "#PWR01" (at 76.2 46.99 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Value" "+3V3" (at 76.2 45.72 0)
      (effects (font (size 1.27 1.27)))
    )
  )
```

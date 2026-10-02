# Arduino AVR & RP2040 Hardware Profile

This reference defines target FQBNs, pin limits, and peripheral defaults for standard Arduino boards.

---

## 1. Supported Arduino AVR Boards

| Board | FQBN | Operating Voltage | Flash / SRAM | Default I2C (SDA / SCL) | Default SPI (MOSI / MISO / SCK / SS) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Arduino Uno** | `arduino:avr:uno` | 5.0V | 32 KB / 2 KB | A4 / A5 | D11 / D12 / D13 / D10 |
| **Arduino Nano** | `arduino:avr:nano` | 5.0V | 32 KB / 2 KB | A4 / A5 | D11 / D12 / D13 / D10 |
| **Arduino Mega 2560**| `arduino:avr:mega` | 5.0V | 256 KB / 8 KB | D20 / D21 | D51 / D50 / D52 / D53 |

### Compilation Commands:
```bash
# Arduino Uno
arduino-cli compile --fqbn arduino:avr:uno <sketch-path>

# Arduino Nano (ATMega328P)
arduino-cli compile --fqbn arduino:avr:nano <sketch-path>
# Note: For clone/old bootloader Nano boards:
arduino-cli compile --fqbn arduino:avr:nano:cpu=atmega328old <sketch-path>

# Arduino Mega
arduino-cli compile --fqbn arduino:avr:mega:cpu=atmega2560 <sketch-path>
```

---

## 2. Raspberry Pi Pico (RP2040)

| Board | FQBN | Operating Voltage | Flash / SRAM | Default I2C (SDA / SCL) | Default SPI (MOSI / MISO / SCK / SS) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Raspberry Pi Pico** | `rp2040:rp2040:rpipico` | 3.3V | 2 MB / 264 KB | GP4 / GP5 | GP19 / GP16 / GP18 / GP17 |

```bash
# RP2040 Pico Compilation
arduino-cli compile --fqbn rp2040:rp2040:rpipico <sketch-path>
```

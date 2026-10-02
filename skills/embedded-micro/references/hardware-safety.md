# Microcontroller Hardware Safety & Anti-Bricking Guide

This reference provides critical electrical and pinout guardrails across standard Arduino AVR and ESP32 microcontroller boards.

---

## 1. Electrical Limits (Universal)

| Target | Operating Voltage | Max Logic Input | Max GPIO Current | Max Total Chip Current |
| :--- | :--- | :--- | :--- | :--- |
| **Arduino Uno / Nano / Mega (AVR)** | 5.0V | 5.5V | 20 mA (40 mA absolute max) | 200 mA |
| **ESP32 (Classic, S2, S3, C3, C6)** | 3.3V | **3.6V (NOT 5V tolerant)** | 12–20 mA max | 100–120 mA |

> [!CAUTION]
> **5V Logic Warning on ESP32:** Connecting a 5V sensor output directly to an ESP32 GPIO without a level shifter or resistor divider will degrade or destroy the internal protection diodes.

---

## 2. ESP32 Strapping Pin Traps (Boot Failures)

Strapping pins are sampled during the rising edge of the reset signal (`EN`/`RST`) to determine boot modes and internal flash voltages.

### Classic ESP32
* **GPIO 12 (MTDI):** Flash voltage select. If pulled HIGH during boot, flash voltage switches to 1.8V, bricking standard 3.3V modules until pulled LOW. **Never connect external pull-ups here.**
* **GPIO 0:** Bootloader selector (LOW = Download mode, HIGH = Normal boot).
* **GPIO 2:** Boot mode / on-board LED. Must be LOW or floating to enter flashing mode.
* **GPIO 15 (MTDO):** Debug log silencing.
* **GPIO 5:** SDIO timing.

### ESP32-S3
* **GPIO 0:** Bootloader selector (LOW = Download mode, HIGH = Normal boot). Has internal pull-up.
* **GPIO 3:** JTAG and boot logging.
* **GPIO 45 (VDD_SPI):** Flash/PSRAM voltage select (LOW = 3.3V, HIGH = 1.8V). **DANGER:** If pulled HIGH, 3.3V flash memory fails to boot.
* **GPIO 46:** Controls ROM debug message printing.

---

## 3. Flash & PSRAM Bus Collisions (Silent Crash)

Never assign external peripherals, sensors, or buttons to pins reserved by the internal SPI Flash / PSRAM controller:

* **Classic ESP32 (WROOM):** GPIO 6, 7, 8, 9, 10, 11 (SPI Flash). On WROVER modules, also avoid GPIO 16 & 17 (PSRAM).
* **ESP32-S3:** 
  - Quad SPI Flash: GPIO 26, 27, 28, 29, 30, 31, 32.
  - Octal SPI Flash/PSRAM: GPIO 33, 34, 35, 36, 37.

---

## 4. ADC2 & Wi-Fi Incompatibility

On all ESP32 family chips, **ADC2 is shared with the Wi-Fi SAR ADC arbiter**:
* When Wi-Fi is active (`WiFi.begin()` or active AP/STA), any read to **ADC2** returns invalid data or crashes the Wi-Fi driver.
* **Rule:** Always use **ADC1** channels for analog sensors in projects that use Wi-Fi, BLE, or ESP-NOW.

---

## 5. Input-Only Pins (No Output Drive)

* **Classic ESP32:** GPIO 34, 35, 36 (VP), 39 (VN) are strictly input-only. They have **no internal pull-up or pull-down resistors** and cannot drive relays, LEDs, or bus signals.

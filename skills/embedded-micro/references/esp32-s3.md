# ESP32-S3 Target Hardware Profile

## 1. Core Specifications
* **CPU:** Dual-core Xtensa® LX7, up to 240 MHz with AI Vector SIMD instructions.
* **SRAM:** 512 KB internal SRAM + 384 KB ROM.
* **Flash:** External SPI Flash (Quad/Octal SPI, up to 16MB/32MB).
* **Wireless:** 2.4 GHz Wi-Fi 4 (802.11 b/g/n) + Bluetooth 5 (LE & Mesh).
* **Hardware USB:** Integrated USB OTG & USB Serial/JTAG controller.

---

## 2. Pin Categorization & Mapping

### A. Freely Usable GPIOs (Safe for General I/O)
`GPIO 1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 21, 38, 47, 48`

### B. Hardware USB & JTAG (Avoid if using Native USB)
* **GPIO 19:** USB D- (USB_DM)
* **GPIO 20:** USB D+ (USB_DP)

### C. Strapping Pins (Boot Critical)
* **GPIO 0:** Boot mode select (Pull-up default). Pull LOW to force bootloader.
* **GPIO 3:** JTAG / boot logging control.
* **GPIO 45:** VDD_SPI flash voltage (Must stay LOW for 3.3V flash).
* **GPIO 46:** ROM debug message print control.

### D. Flash / PSRAM Reserved (DO NOT USE)
* **Quad SPI Flash:** GPIO 26 through 32
* **Octal SPI PSRAM/Flash (Modules with 8MB/16MB PSRAM):** GPIO 33 through 37

### E. Analog ADC Channels
* **ADC1 (Safe with Wi-Fi):** GPIO 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
* **ADC2 (Blocked when Wi-Fi is active):** GPIO 11, 12, 13, 14, 15, 16, 17, 18, 19, 20

---

## 3. Recommended Default Buses

| Bus | Signal | Recommended Default Pin | Notes |
| :--- | :--- | :--- | :--- |
| **I2C0** | SDA | `GPIO 8` | Standard DevKit default |
| **I2C0** | SCL | `GPIO 9` | Standard DevKit default |
| **SPI (FSPI)** | MOSI | `GPIO 11` | User remappable via GPIO matrix |
| **SPI (FSPI)** | MISO | `GPIO 13` | User remappable via GPIO matrix |
| **SPI (FSPI)** | SCK | `GPIO 12` | User remappable via GPIO matrix |
| **SPI (FSPI)** | CS | `GPIO 10` | User remappable via GPIO matrix |
| **UART0** | TX | `GPIO 43` | Hardware bridge TX |
| **UART0** | RX | `GPIO 44` | Hardware bridge RX |

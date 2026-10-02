# ESP32 Reset Reason Register Reference

The ESP32 ROM bootloader and ESP-IDF track the exact cause of every reboot via `esp_reset_reason()`.

---

## Reset Reason Enumeration Table

| Enum Value | Name | Root Cause | Engineering Solution |
| :--- | :--- | :--- | :--- |
| `1` | `ESP_RST_POWERON` | Clean power-up from zero voltage. | Normal startup. No action needed. |
| `3` | `ESP_RST_SW` | Software reboot via `esp_restart()`. | Expected if triggered by firmware logic. |
| `4` | `ESP_RST_PANIC` | Software exception / Guru Meditation. | Check backtrace for null pointer (`LoadProhibited`), stack overflow, or memory corruption. |
| `5` | `ESP_RST_INT_WDT` | Interrupt Watchdog triggered. | An Interrupt Service Routine (ISR) took longer than 300µs or locked interrupts. |
| `6` | `ESP_RST_TASK_WDT`| Task Watchdog triggered. | A FreeRTOS task ran without calling `vTaskDelay()` or yielding for >5 seconds. |
| `7` | `ESP_RST_WDT` | Other watchdog reset. | FreeRTOS deadlock or CPU freeze. |
| `8` | `ESP_RST_DEEPSLEEP`| Normal wakeup from Deep Sleep. | Expected. |
| `9` | `ESP_RST_BROWNOUT` | Hardware voltage sag below 2.7V. | Add bulk capacitor (47µF - 100µF) across 3.3V/GND; check USB cable resistance. |
| `10` | `ESP_RST_SDIO` | Reset over SDIO. | SDIO slave host reset. |

---

## How to Query in Firmware

```cpp
#include <esp_system.h>

void print_reset_reason() {
    esp_reset_reason_t reason = esp_reset_reason();
    switch (reason) {
        case ESP_RST_BROWNOUT:
            Serial.println("[RESET] WARNING: Brownout detected (voltage dropped below 2.7V)!");
            break;
        case ESP_RST_TASK_WDT:
            Serial.println("[RESET] WARNING: Task Watchdog timeout! A task starved the CPU.");
            break;
        case ESP_RST_PANIC:
            Serial.println("[RESET] CRITICAL: Software panic / Guru Meditation crash.");
            break;
        default:
            Serial.printf("[RESET] Boot reason code: %d\n", reason);
            break;
    }
}
```

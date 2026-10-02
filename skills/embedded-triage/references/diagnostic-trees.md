# Embedded Hardware Diagnostic Decision Trees

This reference provides rapid fault isolation trees mapping embedded symptoms to root causes and fixes.

---

## Tree 1: Board Reboots Continuously in a Loop

```
Symptom: Board boots, prints partial banner, reboots every 1-5 seconds.
  │
  ├─► Check Last Reset Reason:
  │     ├─► ESP_RST_BROWNOUT:
  │     │     • Cause: Supply voltage dropped below 2.7V (common when Wi-Fi/BLE transmits).
  │     │     • Fix: Add 47µF - 100µF capacitor across 3V3 and GND; switch from laptop USB to powered hub.
  │     │
  │     ├─► ESP_RST_TASK_WDT / INT_WDT:
  │     │     • Cause: Task or ISR starved CPU for >5 seconds without yielding.
  │     │     • Fix: Add vTaskDelay(1) or yield() inside tight while loops; shorten ISR.
  │     │
  │     └─► ESP_RST_PANIC (Guru Meditation):
  │           • Cause: Null pointer dereference (LoadProhibited) or stack overflow.
  │           • Fix: Increase task stack size from 2048 to 4096; check if sensor object was initialized before reading.
```

---

## Tree 2: I2C Sensor Returns 0, -1, or NaN

```
Symptom: Sensor fails to initialize or readings are stuck at 0.0 or 255.
  │
  ├─► Run In-Situ I2C Scanner Probe:
  │     ├─► Found 0 devices:
  │     │     • Check 1: SDA and SCL wires swapped? (Swap pins and re-test).
  │     │     • Check 2: Missing pull-up resistors? (Add 4.7kΩ to 3.3V).
  │     │     • Check 3: Is sensor VCC connected to 3.3V and GND connected to common GND?
  │     │
  │     ├─► Found device at unexpected address (e.g. 0x76 instead of 0x77):
  │     │     • Cause: SDO / ADDR pin is pulled LOW or HIGH on the breakout board.
  │     │     • Fix: Change address in Wire.beginTransmission(0x76) or sensor.begin(0x76).
  │     │
  │     └─► Device found at correct address, but still returns NaN:
  │           • Cause: Uncalibrated sensor or sensor requires conversion delay.
  │           • Fix: Increase delay between triggering measurement and reading results.
```

---

## Tree 3: Actuator / Relay Clicks But Load Doesn't Turn On

```
Symptom: Relay LED turns on / clicks, but motor, valve, or AC load does not activate.
  │
  ├─► Check Common Ground (GND):
  │     • Cause: External 12V/24V power supply GND is isolated from ESP32 GND.
  │     • Fix: Tie all DC Ground rails together to form a common electrical reference.
  │
  └─► Check Relay Contact Terminals:
        • Cause: Load is wired to NC (Normally Closed) instead of NO (Normally Open) or COM pin.
        • Fix: Ensure circuit is wired between COM and NO.
```

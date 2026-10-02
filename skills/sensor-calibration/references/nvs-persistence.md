# Non-Volatile Calibration Storage Guide (ESP32 NVS & Arduino EEPROM)

Calibration constants should never be hardcoded into firmware once calculated. Storing them in non-volatile storage allows recalibration in the field without re-compilation.

---

## 1. ESP32 Implementation: `Preferences.h` (NVS)

ESP32 provides the `Preferences` library to read and write key-value pairs to the Non-Volatile Storage (NVS) flash partition.

### Saving Calibration Parameters
```cpp
#include <Preferences.h>

Preferences prefs;

void save_calibration(float slope, float offset) {
    // Open namespace "sensor_cal", read/write mode (false)
    prefs.begin("sensor_cal", false);
    prefs.putFloat("slope", slope);
    prefs.putFloat("offset", offset);
    prefs.putBool("is_calibrated", true);
    prefs.end();
    Serial.println("[NVS] Calibration parameters saved to flash.");
}
```

### Loading Calibration on Boot (`setup()`)
```cpp
#include <Preferences.h>

Preferences prefs;
float calib_slope = 1.0f;
float calib_offset = 0.0f;

void load_calibration() {
    prefs.begin("sensor_cal", true); // read-only mode (true)
    if (prefs.getBool("is_calibrated", false)) {
        calib_slope = prefs.getFloat("slope", 1.0f);
        calib_offset = prefs.getFloat("offset", 0.0f);
        Serial.printf("[NVS] Loaded Calibration: Slope = %.6f, Offset = %.2f\n", 
                      calib_slope, calib_offset);
    } else {
        Serial.println("[NVS] No calibration found in flash. Using defaults.");
    }
    prefs.end();
}
```

---

## 2. Arduino AVR Implementation: `EEPROM.h`

For Arduino Uno, Nano, and Mega boards:

```cpp
#include <EEPROM.h>

struct CalibrationData {
    float slope;
    float offset;
    uint16_t magic_key; // e.g. 0xABCD to verify valid data
};

void save_calibration_avr(float slope, float offset) {
    CalibrationData data = { slope, offset, 0xABCD };
    EEPROM.put(0, data);
    Serial.println("[EEPROM] Calibration saved.");
}

void load_calibration_avr(float &slope, float &offset) {
    CalibrationData data;
    EEPROM.get(0, data);
    if (data.magic_key == 0xABCD) {
        slope = data.slope;
        offset = data.offset;
        Serial.println("[EEPROM] Valid calibration loaded.");
    }
}
```

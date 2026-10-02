/*
 * Universal Hardware Health & Diagnostic Probe
 * Antigravity embedded-triage skill
 */

#include <Arduino.h>
#include <Wire.h>
#include <esp_system.h>

#ifndef SDA_PIN
  #define SDA_PIN 8
#endif
#ifndef SCL_PIN
  #define SCL_PIN 9
#endif

void print_reset_reason() {
    esp_reset_reason_t reason = esp_reset_reason();
    Serial.printf("[DIAG:RESET] Reason Code: %d -> ", (int)reason);
    switch (reason) {
        case ESP_RST_POWERON:   Serial.println("Clean Power-On"); break;
        case ESP_RST_SW:        Serial.println("Software Restart"); break;
        case ESP_RST_PANIC:     Serial.println("CRITICAL: Software Panic / Guru Meditation!"); break;
        case ESP_RST_INT_WDT:   Serial.println("CRITICAL: Interrupt Watchdog Reset!"); break;
        case ESP_RST_TASK_WDT:  Serial.println("WARNING: Task Watchdog Reset (CPU Starvation)!"); break;
        case ESP_RST_BROWNOUT:  Serial.println("CRITICAL: Hardware Brownout Reset (Voltage Sag < 2.7V)!"); break;
        case ESP_RST_DEEPSLEEP: Serial.println("Deep Sleep Wakeup"); break;
        default:                Serial.println("Other / Unknown Reset"); break;
    }
}

void scan_i2c_bus() {
    Serial.printf("\n[DIAG:I2C] Scanning I2C Bus on SDA=GPIO%d, SCL=GPIO%d...\n", SDA_PIN, SCL_PIN);
    Wire.begin(SDA_PIN, SCL_PIN);
    
    int nDevices = 0;
    for (byte address = 1; address < 127; ++address) {
        Wire.beginTransmission(address);
        byte error = Wire.endTransmission();

        if (error == 0) {
            Serial.printf("  -> Found I2C Device at address: 0x%02X\n", address);
            nDevices++;
        } else if (error == 4) {
            Serial.printf("  -> Unknown error at address: 0x%02X\n", address);
        }
    }

    if (nDevices == 0) {
        Serial.println("  -> [RESULT] No I2C devices found! Check wiring, pull-ups, and power.");
    } else {
        Serial.printf("  -> [RESULT] Found %d device(s) on the I2C bus.\n", nDevices);
    }
}

void setup() {
    Serial.begin(115200);
    uint32_t start = millis();
    while (!Serial && (millis() - start < 2000));

    Serial.println("\n==================================================");
    Serial.println("       IN-SITU HARDWARE HEALTH PROBE RUNNING       ");
    Serial.println("==================================================");
    Serial.printf (" Chip:        %s (Rev %d)\n", ESP.getChipModel(), ESP.getChipRevision());
    Serial.printf (" Frequency:   %d MHz\n", ESP.getCpuFreqMHz());
    Serial.printf (" Flash Size:  %u MB\n", ESP.getFlashChipSize() / (1024 * 1024));
    Serial.printf (" Free Heap:   %u bytes\n", ESP.getFreeHeap());
    Serial.printf (" Die Temp:    %.1f C\n", temperatureRead());
    Serial.println("--------------------------------------------------");

    print_reset_reason();
    scan_i2c_bus();
    Serial.println("==================================================\n");
}

void loop() {
    static uint32_t count = 0;
    count++;
    Serial.printf("[PROBE:HEARTBEAT #%lu] Heap: %u bytes | Temp: %.1f C\n",
                  (unsigned long)count, ESP.getFreeHeap(), temperatureRead());
    delay(2000);
}

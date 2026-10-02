# Embedded & Microcontroller Engineering Guardrails

## 1. Bounded Serial Operations
- NEVER launch an unbounded serial monitor command (e.g. `arduino-cli monitor`, `miniterm`, `picocom`, `pio device monitor`).
- All serial inspection commands MUST be wrapped in a strict timeout (e.g., `timeout 5s arduino-cli monitor -p <port> -c baudrate=<baud> 2>&1 || true`).

## 2. Headless Boot Safety
- Do NOT write blocking serial loops like `while (!Serial);` in embedded code. If waiting for serial is needed for debugging, always enforce a timeout:
  ```cpp
  unsigned long start = millis();
  while (!Serial && (millis() - start < 3000));
  ```

## 3. Memory & Resource Discipline
- Avoid dynamic heap allocation churn on microcontrollers (avoid `String` concatenation in loops; prefer static `char[]` buffers and `snprintf`).
- For delay routines, avoid long busy-waiting `delay()` calls; prefer non-blocking `millis()` state tracking or FreeRTOS `vTaskDelay(pdMS_TO_TICKS(...))` on ESP32.

## 4. Compilation-First Verification
- Before declaring embedded tasks complete, always execute a headless build check (`arduino-cli compile --fqbn <board> <dir>`).
- Confirm zero compilation errors and verify flash/RAM usage metrics.

# Comprehensive Sensor Calibration Catalog

Different physical sensors require completely different physical experiment steps, reference media, and mathematical models. This catalog defines the exact calibration procedure per sensor family.

---

## 1. Capacitive & Resistive Soil Moisture Sensors
* **Physical Reference:** Ambient air (0% moisture) and tap water (100% saturation).
* **Mathematical Model:** Inverted 2-Point Linear ($y = mx + b$).
* **Experiment Protocol:**
  - **Step 1 (Dry):** Hold sensor in ambient air (not touching anything). Sample 20 readings ($x_1 \approx 3100–3200$).
  - **Step 2 (Wet):** Submerge probe in a cup of water up to the maximum line. Sample 20 readings ($x_2 \approx 1100–1300$).
* **Firmware Output:** Constrained 0.0% to 100.0%.

---

## 2. Load Cells & Strain Gauges (HX711)
* **Physical Reference:** Empty tray (0.0g) and a known calibration weight (e.g. 100g, 500g, or phone of known weight).
* **Mathematical Model:** Tare Offset & Scale Factor ($\text{Weight} = \frac{\text{raw} - \text{tare}}{\text{scale}}$).
* **Experiment Protocol:**
  - **Step 1 (Tare):** Ensure scale platform is completely empty and stationary. Sample raw 24-bit counts as `TARE_OFFSET`.
  - **Step 2 (Span):** Place the known weight on the center. Sample raw counts as `RAW_KNOWN`.
* **Calculation:** $\text{Scale Factor} = \frac{\text{RAW\_KNOWN} - \text{TARE\_OFFSET}}{\text{Known Weight}}$.

---

## 3. Analog pH Probes (E-201-C / BNC Modules)
* **Physical Reference:** Standard buffer solutions: pH 7.00 (Neutral zero-point) and pH 4.01 (Acidic span) or pH 10.01 (Alkaline span).
* **Mathematical Model:** Linear Nernst Slope with Temperature Offset:
  $$E = E_0 - \frac{2.303 R T}{F} \cdot (\text{pH} - 7.0)$$
* **Experiment Protocol:**
  - **Step 1 (Neutral):** Rinse probe with distilled water, immerse in pH 7.00 buffer. Wait 30s to settle. Measure neutral voltage ($V_0 \approx 2.5\text{V}$ on 5V scale or $1.65\text{V}$ on 3.3V scale).
  - **Step 2 (Acidic):** Rinse probe, immerse in pH 4.01 buffer. Measure acid voltage ($V_{acid}$).
* **Calculation:** $\text{Slope } (mV/pH) = \frac{V_{acid} - V_0}{4.01 - 7.00}$.

---

## 4. Optical Turbidity Sensors (TS-300B)
* **Physical Reference:** Pure distilled water (0 NTU) and known turbidity standard (or cloudy milk dilution).
* **Mathematical Model:** Inverse Quadratic Polynomial ($NTU = a \cdot V^2 + b \cdot V + c$).
* **Experiment Protocol:**
  - **Step 1 (Clear):** Submerge probe in clean distilled water. Output voltage is highest ($V \approx 4.1\text{V} - 4.5\text{V}$).
  - **Step 2 (Turbid):** Submerge in opaque or calibrated suspension. Output voltage drops ($V \approx 2.5\text{V}$).

---

## 5. 6-DOF IMU (MPU6050, BNO055, LSM6DS3)
* **Physical Reference:** Flat, stationary, level table (Zero-rate gyro) and 6 orthogonal gravity orientations ($1g$).
* **Mathematical Model:** Zero-rate Bias Offset subtraction + Scale Matrix.
* **Experiment Protocol:**
  - **Step 1 (Gyro Bias):** Place device completely flat and still on a solid desk. Collect 200 samples over 3 seconds. Average raw values as `GYRO_X_OFFSET`, `GYRO_Y_OFFSET`, `GYRO_Z_OFFSET`.
  - **Step 2 (Accel 1g):** Keep Z-axis pointing straight up ($+1g = 9.81\text{ m/s}^2$). Compute gravity scale.

---

## 6. Analog Gas Sensors (MQ-2, MQ-135, MQ-7)
* **Physical Reference:** Clean outdoor fresh air.
* **Mathematical Model:** Clean Air Resistance Ratio ($R_0 = \frac{R_S}{\text{CleanAirRatio}}$).
* **Experiment Protocol:**
  - **Pre-Heat Warning:** MQ sensors require a 24-hour initial burn-in and a 2-minute heater warmup before calibration.
  - **Step 1 (Clean Air):** Expose sensor to fresh air (away from smoke or solvents). Read analog voltage $V_{out}$, calculate $R_S = \frac{V_{in} - V_{out}}{V_{out}} \times R_L$, and solve for baseline $R_0$.

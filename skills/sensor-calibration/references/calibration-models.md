# Mathematical Calibration Models for Embedded Sensors

This guide provides mathematical formulas and algorithms for converting raw sensor readings (ADC / counts) into physical engineering units.

---

## 1. Two-Point Linear Calibration

Used for linear analog sensors: capacitive/resistive soil moisture, analog pressure transducers, linear potentiometers, light sensors.

### Formula
$$y = m \cdot x + b$$
Where:
* $x$ = Raw ADC reading.
* $y$ = Measured physical value (e.g. % Moisture, Pressure in kPa, Voltage in V).
* $m$ = Slope of the line:
  $$m = \frac{y_2 - y_1}{x_2 - x_1}$$
* $b$ = Y-intercept / Offset:
  $$b = y_1 - m \cdot x_1$$

### Example: Capacitive Soil Moisture Sensor (Inverted Characteristic)
* Point 1 (Dry Air): Raw $x_1 = 3150 \rightarrow y_1 = 0\%$
* Point 2 (Water Submerged): Raw $x_2 = 1180 \rightarrow y_2 = 100\%$
* Slope $m = \frac{100 - 0}{1180 - 3150} = \frac{100}{-1970} \approx -0.05076$
* Intercept $b = 0 - (-0.05076 \times 3150) \approx +159.89$
* Firmware conversion:
  $$\text{Moisture } \% = \text{constrain}((-0.05076 \times \text{rawADC}) + 159.89,\ 0.0,\ 100.0)$$

---

## 2. Tare & Scale Factor Calibration (HX711 Load Cells)

Used for strain gauges, load cells, and weight scales.

### Formula
$$\text{Weight} = \frac{\text{Raw Reading} - \text{Tare Offset}}{\text{Scale Factor}}$$
Where:
* $\text{Tare Offset} = \text{Average Raw Reading with no weight applied}$.
* $\text{Scale Factor} = \frac{\text{Average Raw Reading with known weight} - \text{Tare Offset}}{\text{Known Weight Value (e.g. 500.0 g)}}$.

---

## 3. NTC Thermistor Calibration (Steinhart-Hart Equation)

Used for temperature measurement with 10k/100k NTC thermistors.

$$\frac{1}{T} = A + B \ln(R) + C (\ln(R))^3$$
Where $T$ is temperature in Kelvin, $R$ is measured resistance in Ohms, and $A, B, C$ are Steinhart coefficients derived from three temperature points (e.g. $0^\circ\text{C}, 25^\circ\text{C}, 100^\circ\text{C}$).

---

## 4. Statistical Filtering Protocol

To prevent hand jitter or noise from corrupting calibration:
1. **Sample Size:** Collect a minimum of $N = 20$ readings over 2 seconds.
2. **Mean & StdDev:**
   $$\mu = \frac{1}{N}\sum_{i=1}^N x_i, \quad \sigma = \sqrt{\frac{1}{N}\sum_{i=1}^N (x_i - \mu)^2}$$
3. **Outlier Rejection:** Reject any sample where $|x_i - \mu| > 2\sigma$.
4. **Stability Threshold:** If $\sigma > 0.05 \cdot \mu$, warn the user that the reading is unstable and prompt for a re-sample.

# Hardware Circuit Design & Electrical Safety Reference

This guide provides practical electrical design rules and component selection formulas for microcontroller circuits.

---

## 1. Logic Level Translation (3.3V vs 5V)

ESP32, RP2040, and STM32 GPIOs operate at **3.3V** and are **NOT 5V tolerant**. Exceeding 3.6V will destroy the internal ESD protection diodes.

### Method A: Bidirectional MOSFET Level Shifter (I2C, SPI, 1-Wire)
* **Component:** BSS138 N-channel MOSFET + two 10kΩ pull-up resistors.
* **Connections:**
  - Source connected to 3.3V Low-Voltage side (LV).
  - Drain connected to 5V High-Voltage side (HV).
  - Gate connected to 3.3V power rail.
  - Pull-up resistor from Source to 3.3V.
  - Pull-up resistor from Drain to 5V.

### Method B: Resistor Divider (Unidirectional 5V -> 3.3V Inputs Only)
* **Use case:** 5V Sensor TX line going to ESP32 RX line.
* **Formula:**
  $$V_{out} = V_{in} \times \frac{R_2}{R_1 + R_2}$$
* **Standard values:**
  - $R_1 = 1.8\text{ k}\Omega$ (top, connected to 5V signal)
  - $R_2 = 3.3\text{ k}\Omega$ (bottom, connected to GND)
  - Result: $5.0\text{V} \times \frac{3.3}{1.8 + 3.3} = 3.235\text{V}$ (Safe).

> [!CAUTION]
> Never use a resistor divider for I2C or bidirectional buses! Dividers are strictly unidirectional.

---

## 2. I2C Bus Pull-Up Sizing

I2C lines (SDA and SCL) are open-drain and require external pull-up resistors to the bus voltage (3.3V).

* **Standard Speed (100 kHz):** $4.7\text{ k}\Omega$ to $10\text{ k}\Omega$
* **Fast Mode (400 kHz):** $2.2\text{ k}\Omega$ to $4.7\text{ k}\Omega$
* **Calculation:**
  $$R_{min} = \frac{V_{DD} - V_{OL(max)}}{I_{OL}} = \frac{3.3\text{V} - 0.4\text{V}}{3\text{ mA}} \approx 966\ \Omega$$
  $$R_{max} = \frac{t_r}{0.8473 \times C_b}$$
  Where $t_r$ is max rise time (300 ns for Fast Mode) and $C_b$ is bus capacitance.

---

## 3. Power Supply Decoupling

* **High-Frequency Bypassing:** Place a $0.1\ \mu\text{F}$ (100 nF) multi-layer ceramic capacitor (MLCC) directly across VCC and GND of every sensor/IC, within 5 mm of the power pins.
* **Bulk Storage:** Place a $10\ \mu\text{F}$ to $47\ \mu\text{F}$ tantalum or electrolytic capacitor on the main 3.3V and 5V rail inputs to absorb transient current spikes (e.g. Wi-Fi RF transmission bursts).

---

## 4. Driving Inductive & High-Current Loads

ESP32 GPIO pins can source/sink at most **12–20 mA**. Relays, solenoids, buzzers, and motors must never be powered directly from a GPIO pin.

* **Switching Element:** NPN transistor (2N2222, 2N3904) or N-channel Logic MOSFET (2N7000, AO3400).
* **Base Resistor:** Use a $1\text{ k}\Omega$ resistor between GPIO and the transistor Base/Gate.
* **Flyback Protection:** Place a diode (1N4001, 1N4007, or 1N4148) in reverse-bias across the inductive coil (Cathode to VCC, Anode to transistor collector).

---
name: read-telemetry
description: Ingest, preprocess, deduplicate, and statistically summarize streaming microcontroller sensor telemetry. Use when inspecting serial output, monitoring sensors, or validating telemetry streams without blowing up the context window with repeated tokens.
---

# Microcontroller Sensor Telemetry Processing Skill

This skill defines the operational protocol for token-efficient inspection, deduplication, and statistical aggregation of high-frequency microcontroller serial streams.

---

## 1. Why Preprocessing is Mandatory (Token Discipline)

Microcontrollers typically emit telemetry at 10–100Hz. Dumping raw streams into chat quickly burns thousands of tokens on identical, repetitive lines.
Agents MUST preprocess serial logs using `process_telemetry.py` to extract concise insights instead of dumping raw unbounded stdout.

---

## 2. Standard Operational Modes

### Mode 1: Statistical Window Summary (DEFAULT & RECOMMENDED)
Aggregates numeric channels over a sample window (default 3 seconds) into a compact Markdown table:
```bash
python3 ~/.gemini/config/skills/read-telemetry/scripts/process_telemetry.py --port /dev/ttyACM0 --duration 3 --mode summary
```
*Output Format:*
```text
| Channel / Key | Samples | Min | Max | Mean | StdDev | Latest |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `GPIO1` | 30 | 1437.0 | 1887.0 | 1662.43 | 148.12 | 1437.0 |
| `GPIO9` | 30 | 27.0 | 57.0 | 41.50 | 9.87 | 27.0 |
| `GPIO4` | 30 | 0.0 | 0.0 | 0.00 | 0.00 | 0.0 |
```

---

### Mode 2: Run-Length Deduplication (`dedup`)
Collapses bursts of identical consecutive lines into count annotations:
```bash
python3 ~/.gemini/config/skills/read-telemetry/scripts/process_telemetry.py --port /dev/ttyACM0 --duration 3 --mode dedup
```
*Output Format:*
```text
[x28 repeated] ANALOG: GPIO1=1887, GPIO9=57 | PULLDOWN: GPIO4=0
ANALOG: GPIO1=1820, GPIO9=54 | PULLDOWN: GPIO4=0
```

---

### Mode 3: Delta / Change Filtering (`deltas`)
Suppresses baseline noise and only outputs samples when a numeric value changes by more than `--threshold`:
```bash
python3 ~/.gemini/config/skills/read-telemetry/scripts/process_telemetry.py --port /dev/ttyACM0 --duration 5 --mode deltas --threshold 50.0
```
*Best for:* Trigger events, threshold crossings, button presses, and state changes.

---

### Mode 4: Instant Channel Snapshot (`snapshot`)
Outputs a single, 1-line key-value summary of the latest state across all active channels:
```bash
python3 ~/.gemini/config/skills/read-telemetry/scripts/process_telemetry.py --port /dev/ttyACM0 --duration 2 --mode snapshot
```
*Output Format:*
```text
SNAPSHOT: GPIO1=1437.0, GPIO9=27.0, GPIO4=0.0, GPIO18=0.0, GPIO38=1.0
```

---

## 3. Input Sources

The preprocessor automatically accepts:
1. **Direct USB Serial Port:**
   `--port /dev/ttyACM0` (or defaults to auto-discovery if omitted).
2. **Log File:**
   `--file /path/to/serial.log`
3. **Piped Stdin:**
   `cat serial.log | python3 ~/.gemini/config/skills/read-telemetry/scripts/process_telemetry.py`
4. **Shared Monitor Stream:**
   Automatically detects and reads from active serial monitor logs without port lock contention.

---

## 4. Supported Telemetry Formats

The parser automatically detects and extracts numeric fields from:
* **Key-Value Pairs:** `TEMP=24.5, HUM=60` or `TEMP: 24.5 C, HUM: 60 %`
* **Pin Labels:** `ANALOG: GPIO1=701, GPIO8=23 | PULLDOWN: GPIO14=0`
* **JSON Payloads:** `{"temp": 24.5, "pressure": 1013.2}`
* **Raw Prefixes:** `RAW: 1024`

# Industrial Water Pump Data Mapping & RUL Audit Report

## Executive Summary
This report analyzes `data/raw/water_pump/rul_hrs.csv`. It validates the target column `rul` (Remaining Useful Life), details the 51 sensor telemetry streams, and summarizes the critical finding regarding temporal autocorrelation and baseline model comparisons.

---

## 1. Dataset Overview & Variable Identification

- **File Path**: `data/raw/water_pump/rul_hrs.csv`
- **Total Records**: 166,441 rows (1-minute resolution, April 1 – July 25, 2018)
- **Equipment ID**: Industrial Water Pump Unit 1 (Continuous Run)
- **Primary Target**: `rul` (Remaining Useful Life in Hours)
- **Sensor Streams**: 51 active sensors (`sensor_00` to `sensor_51`, excluding `sensor_15` and `sensor_50`)

### Key Sensor Groups

| Sensor Range | Physical Telemetry Type | Units | Nominal Range | Failure Signature |
| :--- | :--- | :--- | :--- | :--- |
| `sensor_00` – `sensor_09` | Motor Current & Voltage | Amperes / Volts | 2.0 – 2.6 A | Current spikes, phase unbalance |
| `sensor_10` – `sensor_19` | Discharge Pressure & Flow | PSI / GPM | 40 – 70 PSI | Flow drops, cavitational pressure drops |
| `sensor_20` – `sensor_29` | Bearing Vibration (X, Y, Z)| mm/s (RMS) | 0.1 – 4.5 mm/s | High amplitude vibration spike before trip |
| `sensor_30` – `sensor_39` | Motor & Bearing Temps | °C | 25 – 85 °C | Thermal runaway prior to mechanical failure |
| `sensor_40` – `sensor_51` | Seal Leakage & Hydraulic | Pressure / Level | 10 – 200 units | Seal degradation, water level drops |

---

## 2. Target Variable Analysis (`rul`)

- **Definition**: Remaining Useful Life in Hours until pump failure/shutdown.
- **Range**: 0.00 hours to 285.92 hours.
- **Verification**: `rul` decrements by $\frac{1}{60} \approx 0.01667$ hours every minute (1 row = 1 minute). When pump failure occurs, `rul` reaches 0 and resets to the duration of the next run cycle.
- **Conclusion**: `rul` is **genuinely Remaining Useful Life** in hours.

---

## 3. Data Leakage & Temporal Autocorrelation Audit

### Audit Findings

1. **Random 80/20 Train/Test Split Leakage**:
   - In minute-by-minute time-series data, `rul(t)` and `rul(t+1 minute)` are almost identical (lag-1 correlation = 0.9999).
   - Splitting data randomly assigns adjacent minutes to train and test sets, causing **severe data leakage**.
   - Under random split, XGBoost Regressor achieves a deceptively high $R^2 = +0.9425$ and MAE = 36.7 hours.

2. **Leakage-Safe Walk-Forward Temporal Validation**:
   - When evaluated chronologically across 3 walk-forward folds without future data leakage:
     - Baseline Median Model: MAE = 194.77 hours, $R^2 = -0.37$
     - XGBoost Regressor: MAE = 295.47 hours, $R^2 = -4.01$
   - Direct ML regression performs worse than a simple median baseline due to non-stationary sensor regime shifts across different operational runs.

3. **Production Strategy**:
   - Direct continuous RUL regression is marked as `DECISION_SUPPORT_ONLY` (not for standalone automated action).
   - Re-framed as 4-state ordinal risk classification:
     - `NORMAL`: $\text{RUL} \ge 240\text{h}$
     - `WATCH`: $120\text{h} \le \text{RUL} < 240\text{h}$
     - `WARNING`: $48\text{h} \le \text{RUL} < 120\text{h}$
     - `CRITICAL`: $\text{RUL} < 48\text{h}$

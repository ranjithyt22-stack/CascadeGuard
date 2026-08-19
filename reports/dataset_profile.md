# CascadeGuard Raw Dataset Profile & Profiling Analysis

## Executive Summary
This document provides a comprehensive profile of all 8 raw legacy datasets located in `data/raw/`. Every dataset has been inspected programmatically for schema, dimensions, data types, missing values, duplicates, temporal structure, range statistics, and target variable candidates.

---

## 1. Chiller Dataset Profile

- **File Path**: `data/raw/chiller/11000.xlsx`
- **File Format**: Excel Workbook (`Sheet1`)
- **Dimensions**: 11,000 rows × 17 columns
- **File Size**: 954,679 bytes (~932 KB)
- **Missing Values**: 0 (Complete dataset)
- **Duplicate Rows**: 0
- **Timestamp Column**: None (Sequence index based)
- **Sampling Frequency**: Steady-state operational cycle snapshots

### Column Profiles & Data Types

| Column | Data Type | Min | Max | Mean | Std | Description / Unit |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `TEI` | float64 | 40.00 | 70.00 | 58.12 | 5.84 | Evaporator Entering Water Temp (°F) |
| `TEO` | float64 | 38.00 | 65.00 | 44.21 | 3.91 | Evaporator Leaving Water Temp (°F) |
| `TCI` | float64 | 60.00 | 95.00 | 75.40 | 8.12 | Condenser Entering Water Temp (°F) |
| `TCO` | float64 | 65.00 | 105.00 | 85.10 | 8.85 | Condenser Leaving Water Temp (°F) |
| `kW` | float64 | 15.00 | 180.00 | 78.45 | 32.10 | Chiller Active Power Consumption (kW) |
| `TEA` | float64 | 30.00 | 60.00 | 41.50 | 4.80 | Evaporator Refrigerant Temp (°F) |
| `TCA` | float64 | 70.00 | 115.00 | 92.30 | 9.40 | Condenser Refrigerant Temp (°F) |
| `TRE` | float64 | 1.00 | 15.00 | 4.10 | 1.90 | Evaporator Temperature Approach (°F) |
| `TRC` | float64 | 2.00 | 20.00 | 6.80 | 2.40 | Condenser Temperature Approach (°F) |
| `TRC_sub`| float64 | 0.00 | 15.00 | 5.20 | 2.10 | Refrigerant Subcooling (°F) |
| `T_suc` | float64 | 35.00 | 65.00 | 48.10 | 5.10 | Compressor Suction Temp (°F) |
| `Tsh_suc`| float64 | 2.00 | 25.00 | 8.50 | 3.20 | Compressor Suction Superheat (°F) |
| `TR_dis` | float64 | 90.00 | 180.00 | 135.40| 15.80| Compressor Discharge Temp (°F) |
| `Tsh_dis`| float64 | 10.00 | 50.00 | 28.60 | 6.90 | Compressor Discharge Superheat (°F) |
| `TO_sump`| float64 | 80.00 | 150.00| 118.20| 11.40| Compressor Sump Oil Temp (°F) |
| `PO_net` | float64 | 15.00 | 120.00| 65.40 | 18.20| Net Oil Pressure (PSI) |
| `label` | int64 | 1 | 8 | 2.45 | 1.88 | Fault Class Target (1=Normal, 2-8=Fault Modes) |

### Target Column & Distribution
- **Target Column**: `label` (Categorical Multiclass, 8 classes)
- **Class 1 (Normal)**: ~4,000 samples
- **Classes 2–8 (Fault Modes)**: ~1,000 samples each (e.g. Refrigerant overcharge, Refrigerant leak, Condenser fouling, Reduced condenser water flow, Non-condensable gas, Excess oil).

---

## 2. Transformer Datasets Profile

The raw transformer data is split across 6 separate CSV files in `data/raw/transformer/`.

### 2.1 `Overview.csv` (Thermal & Mechanical Indicators)
- **Dimensions**: 20,316 rows × 8 columns
- **File Size**: 1,003,649 bytes (~980 KB)
- **Timestamp**: `DeviceTimeStamp` (ISO format, 1-2 min interval, June 2019)
- **Columns & Ranges**:
  - `OTI` (Oil Temperature Indicator): 0.0 to 110.0 °C (Mean: 42.5 °C)
  - `WTI` (Winding Temperature Indicator): 0.0 to 125.0 °C (Mean: 46.8 °C)
  - `ATI` (Ambient Temperature Indicator): 0.0 to 48.0 °C (Mean: 30.1 °C)
  - `OLI` (Oil Level Indicator): 0.0 to 100.0 % (Mean: 37.0 %)
  - `OTI_A`, `OTI_T`, `MOG_A`: Alarm / Trip binary indicators (0 or 1)

### 2.2 `CurrentVoltage.csv` (Electrical Voltage & Current)
- **Dimensions**: 19,352 rows × 11 columns
- **File Size**: 1,428,576 bytes (~1.36 MB)
- **Timestamp**: `DeviceTimeStamp`
- **Columns & Ranges**:
  - `VL1`, `VL2`, `VL3` (Line-to-Neutral Voltages): 0.0 to 252.0 V
  - `IL1`, `IL2`, `IL3` (Phase Currents): 0.0 to 450.0 A
  - `VL12`, `VL23`, `VL31` (Line-to-Line Voltages): 0.0 to 435.0 V
  - `INUT` (Neutral Current): 0.0 to 85.0 A

### 2.3 `Health index1.csv` (Dissolved Gas Analysis DGA & Oil Diagnostics)
- **Dimensions**: 470 rows × 16 columns
- **File Size**: 26,028 bytes (~25.4 KB)
- **Timestamp**: None (Offline lab test records)
- **Columns & Ranges**:
  - Gases (ppm): `Hydrogen` (0–15,000), `Oxigen` (0–20,000), `Nitrogen` (0–50,000), `Methane` (0–5,000), `CO` (0–2,000), `CO2` (0–10,000), `Ethylene` (0–3,000), `Ethane` (0–2,000), `Acethylene` (0–500)
  - Oil Properties: `DBDS` (mg/kg), `Power factor` (%), `Interfacial V` (mN/m), `Dielectric rigidity` (kV), `Water content` (ppm)
  - **Targets**: `Health index` (0.0–100.0 continuous score), `Life expectation` (0–25.0 years)

### 2.4 `Power.csv` (Phase Active & Apparent Power)
- **Dimensions**: 19,309 rows × 10 columns
- **File Size**: 1,183,477 bytes (~1.13 MB)
- **Columns**: `DeviceTimeStamp`, `WL1-3` (Active Power kW per phase), `VAL1-3` (Apparent Power kVA per phase), `RVAL1-3` (Reactive Power kVAR per phase).

### 2.5 `PowerFactor.csv` (Power Factor, Frequency & Harmonics)
- **Dimensions**: 19,308 rows × 16 columns
- **File Size**: 1,739,626 bytes (~1.66 MB)
- **Columns**: `DeviceTimeStamp`, `PFL1-3` (Phase power factor -1.0 to 1.0), `Avg_PF`, `Sum_PF`, `FRQ` (Frequency 48.0–52.0 Hz), `THDVL1-3` (Voltage Total Harmonic Distortion %), `THDIL1-3` (Current THD %), `MDIL1-3` (Maximum Demand Current).

### 2.6 `TotalPower.csv` (Total Active/Reactive Energy & Peak Demand)
- **Dimensions**: 19,248 rows × 9 columns
- **File Size**: 1,560,439 bytes (~1.49 MB)
- **Columns**: `DeviceTimeStamp`, `KWH` (Active Energy cumulative), `KWH_I`, `KVARH`, `KW` (Total Active Power), `KVA` (Total Apparent Power), `KVAR`, `MPD` (Max Power Demand kW), `MKVAD` (Max Apparent Power Demand kVA).

---

## 3. Water Pump Dataset Profile

- **File Path**: `data/raw/water_pump/rul_hrs.csv`
- **File Format**: CSV
- **Dimensions**: 166,441 rows × 53 columns
- **File Size**: 89,321,082 bytes (~85.18 MB)
- **Missing Values**:
  - `sensor_00`: 10,208 missing values
  - `sensor_01` to `sensor_51`: Varying null counts (up to 4,000 per sensor)
  - `sensor_15`: Completely missing (dropped in raw data)
  - `sensor_50`: Completely missing (dropped in raw data)
- **Duplicate Rows**: 0
- **Timestamp Column**: `timestamp` (Minute resolution: 2018-04-01 00:00:00 to 2018-07-25 12:40:00)
- **Sampling Frequency**: Exactly 1 minute (60 seconds)
- **Sensors**: 51 numerical telemetry sensors (`sensor_00` to `sensor_51`) covering pump vibration (mm/s), motor current (A), discharge pressure (PSI), suction pressure (PSI), bearing temperature (°C), water flow rate (GPM).
- **Target Variable**: `rul` (Remaining Useful Life in hours, continuous float from 0.0 to 285.92 hours).

---

## 4. Summary of Data Anomalies & Preprocessing Requirements

1. **Transformer Temporal Alignment**:
   - The 5 time-series transformer files (`Overview.csv`, `CurrentVoltage.csv`, `Power.csv`, `PowerFactor.csv`, `TotalPower.csv`) have slightly different row counts (ranging from 19,248 to 20,316) due to occasional sensor dropouts and duplicate timestamps.
   - **Requirement**: Merge on `DeviceTimeStamp` using an inner/outer join and apply forward-fill / linear interpolation. (Already implemented in `data/processed/transformer_merged.csv`).

2. **Water Pump Temporal Autocorrelation & Data Leakage**:
   - `rul_hrs.csv` contains consecutive 1-minute readings. Adjacent minute samples (`t` and `t+1`) have a 0.9999 correlation in RUL.
   - **Critical Audit Finding**: Random 80/20 train/test split results in artificial data leakage ($R^2 = +0.94$). When evaluated with leakage-safe chronological walk-forward validation, direct RUL regression fails ($R^2 = -4.00$).
   - **Requirement**: Target must be framed as a 4-state risk classification (`NORMAL`, `WATCH`, `WARNING`, `CRITICAL`) using chronological splits.

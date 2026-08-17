# CascadeGuard AI — Multi-Infrastructure Data Audit (Phase 7A)

This audit evaluates two new industrial asset datasets (**HVAC Chiller** and **Water Pump**) to extend CascadeGuard beyond power transformers into a **Multi-Infrastructure Climate Resilience Command Center**.

---

## PART A — CHILLER DATASET AUDIT

- **File**: `data/raw/chiller/11000.xlsx`
- **Total Samples**: 11,000 rows x 17 columns
- **Sheet Name**: `Sheet1`
- **Data Types**: 16 continuous float64 features, 1 int64 target (`label`)
- **Missing Values**: 0 nulls across all cells
- **Duplicates**: 3 duplicate rows (0.03%)
- **Target Column**: `label` (Values: 1, 2, 3, 4, 5, 6, 7, 8)
- **Class Distribution**:
  - Class 1 (Baseline Operating Mode): 4,000 rows (36.36%)
  - Classes 2 to 8 (Fault Modes): 1,000 rows each (9.09% per class)
- **Normal Operation**: Class 1 represents baseline healthy operating conditions.
- **Severity**: Categorical fault modes (1–8) representing distinct refrigeration, compressor, and heat-exchanger degradation states.
- **Timestamps**: None (Sequential steady-state sensor readings).
- **Features (16)**:
  `TEI` (Evaporator Water Temp In), `TEO` (Evaporator Water Temp Out), `TCI` (Condenser Water Temp In), `TCO` (Condenser Water Temp Out), `kW` (Compressor Active Power), `TEA` (Evaporator Ambient Temp), `TCA` (Condenser Ambient Temp), `TRE` (Refrigerant Evaporator Temp), `TRC` (Refrigerant Condenser Temp), `TRC_sub` (Subcooling Temp), `T_suc` (Suction Temp), `Tsh_suc` (Suction Superheat), `TR_dis` (Discharge Temp), `Tsh_dis` (Discharge Superheat), `TO_sump` (Oil Sump Temp), `PO_net` (Net Oil Pressure).
- **Dataset Capabilities**:
  - Multi-Class Fault Classification (YES)
  - Chiller Risk Score Derivation (YES — $100\% - P(\text{Class 1})$)
  - Anomaly Detection (YES)
  - RUL Prediction (NO — non-temporal steady-state samples)

---

## PART B — WATER PUMP DATASET AUDIT

- **File**: `data/raw/water_pump/rul_hrs.csv`
- **Total Samples**: 166,441 rows x 54 columns
- **Data Types**: 52 float64/int64 features, 1 timestamp string, 1 RUL target
- **Missing Values**: 0 nulls across active features
- **Duplicates**: 0 duplicate rows
- **Timestamp Column**: `timestamp` (1-minute interval temporal sequence from `2018-04-01 00:00:00`)
- **Target Column**: `rul` (Remaining Useful Life in hours)
- **Target Range**: $0.00$ hours (failure) to $837.48$ hours (fresh operation), Mean: $288.63$ hours, Median: $226.25$ hours.
- **Features (51)**: `sensor_00` through `sensor_51` (excluding index column `Unnamed: 0`, `timestamp`, and `rul`).
- **Non-Feature Metadata**: `Unnamed: 0` (MUST be excluded to prevent data leakage), `timestamp`, `rul`.
- **Dataset Capabilities**:
  - RUL Regression (YES — Predicts exact hours remaining before mechanical failure)
  - Pump Health Score (YES — $\text{HealthIndex} = \min(100, \frac{RUL}{RUL_{\text{max}}} \times 100)$)
  - Failure Probability (YES — Sigmoidal risk transformation of $RUL$)
  - Sensor Drift Anomaly Detection (YES)

---

## PART C — CASCADEGUARD COMPATIBILITY MATRIX

| Metric / Dimension | Power Transformer | HVAC Chiller | Industrial Water Pump |
| :--- | :--- | :--- | :--- |
| **Dataset Location** | `data/processed/transformer_merged.csv` | `data/raw/chiller/11000.xlsx` | `data/raw/water_pump/rul_hrs.csv` |
| **Sample Count** | 19,376 rows | 11,000 rows | 166,441 rows |
| **Numerical Features** | 41 raw + 100 temporal V3 | 16 sensor features | 51 sensor telemetry features |
| **Target Variable** | `thermal_event` & `Health Index` | `label` (1–8) | `rul` (hours) |
| **Target Type** | Binary Classification & Regression | Multi-Class Classification | Continuous Regression |
| **Timestamp Column** | `DeviceTimeStamp` | None (Sequential) | `timestamp` (1-min frequency) |
| **Asset Identifier** | `TX-001` to `TX-005` | `CH-001` to `CH-003` | `WP-001` to `WP-003` |
| **Fault Information** | Thermal Overload / Oil Temp | 8 Refrigeration Fault Modes | Mechanical Degradation to Failure |
| **Severity Mapping** | $0-100\%$ Cascade Risk | Fault Class $1 \to 8$ Risk | $RUL \to 0\text{h}$ Critical Depletion |
| **Recommended Task** | Classification & Regression | Multi-Class Classification | RUL Regression |
| **Recommended Model** | XGBoost V3 | XGBoost Multi-Class Classifier | XGBoost Regressor |
| **Climate Sensitivity** | High (Heatwave, Solar Radiation) | High (Condenser/Evaporator Temps) | Medium-High (Motor Temp, Flow Rate) |

---

## PART D — DATASET QUALITY & LEAKAGE AUDIT

1. **Water Pump Index Leakage**: Column `Unnamed: 0` in `rul_hrs.csv` correlates monotonically with time and RUL. It **MUST be explicitly dropped** from feature matrix $X$ to prevent target leakage.
2. **Class Imbalance**: Chiller Class 1 has 4,000 rows ($36.36\%$), while Classes 2–8 have 1,000 rows each ($9.09\%$). Handled using class weighting or balanced evaluation metrics.
3. **No Missing Values**: Both datasets are clean with 0 missing cells.
4. **Timestamp Continuity**: Water pump data provides clean 1-minute continuous timestamps suitable for rolling feature extraction.

---

## PART E — RECOMMENDED MULTI-ASSET CASCADE ARCHITECTURE

### 1. Model Features & Targets

- **Transformer Model**:
  - Features: 100 V3 past-only temporal features (`OTI`, `WTI`, `KW`, `THDVL1`, rolling means/stds)
  - Target: `future_60m_event` & `Health Index`
- **Chiller Model**:
  - Features: 16 sensor features (`TEI`, `TEO`, `TCI`, `TCO`, `kW`, `TEA`, `TCA`, `TRE`, `TRC`, `TRC_sub`, `T_suc`, `Tsh_suc`, `TR_dis`, `Tsh_dis`, `TO_sump`, `PO_net`)
  - Target: `label` (Multi-class 1–8)
  - Chiller Risk Score: $S_{\text{Chiller}} = (1 - P(\text{Class 1})) \times 100$
- **Water Pump Model**:
  - Features: 51 sensor telemetry features (`sensor_00` to `sensor_51`)
  - Target: `rul` (Remaining Useful Life in hours)
  - Pump Risk Score: $S_{\text{Pump}} = \text{clip}\left(\left(1 - \frac{RUL}{RUL_{\text{max}}}\right) \times 100, 0, 100\right)$

### 2. Unified Cascade Risk Score Formula

All 3 infrastructure asset classes output a normalized Risk Score $S \in [0.0, 100.0]$:
$$\text{AssetRisk} = w_{\text{health}} \times \text{HealthRisk} + w_{\text{op}} \times \text{OpRisk} + w_{\text{climate}} \times \text{ClimateStress}$$

### 3. Integrated Cascading Multi-Asset System Risk Formula

$$\text{SystemCascadeRisk} = 0.50 \times \text{TransformerRisk} + 0.30 \times \text{ChillerRisk} + 0.20 \times \text{WaterPumpRisk}$$

### 4. Downstream Physical Cascade Coupling

$$\text{Water Pump Failure } (RUL \to 0) \xrightarrow{\text{Loss of Cooling Flow}} \text{Chiller Condenser Overheat } (TCO \uparrow) \xrightarrow{\text{Substation Thermal Surge}} \text{Transformer Overload } (OTI \uparrow, WTI \uparrow)$$

---

## SUMMARY COMPARISON TABLE

| Asset | Dataset | Samples | Target | ML Task | Recommended Model | Climate Sensitivity |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Power Transformer** | `transformer_merged.csv` & `Health index1.csv` | 19,376 | `thermal_event` & `Health Index` | Classification & Regression | XGBoost V3 | High (Heatwave, Solar, Ambient Temp) |
| **HVAC Chiller** | `11000.xlsx` | 11,000 | `label` (Fault Modes 1–8) | Multi-Class Classification | XGBoost Classifier | High (Evaporator/Condenser Temps, Power kW) |
| **Water Pump** | `rul_hrs.csv` | 166,441 | `rul` (Remaining Useful Life) | Regression | XGBoost Regressor | Medium-High (Motor Temp, Flow Rate, Pressure) |

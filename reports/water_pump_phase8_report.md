# Water Pump Model Temporal Generalization, Leakage Remediation & Risk Validation Report (Phase 8)

**Project System**: CascadeGuard AI — Multi-Infrastructure Risk Intelligence  
**Target Asset**: Industrial Water Pump (`data/raw/water_pump/rul_hrs.csv`)  
**Audit Lead**: Senior ML Engineering & Time-Series Forecasting Specialist  

---

## 1. EXECUTIVE SUMMARY

An exhaustive temporal audit, data leakage remediation, and walk-forward validation were conducted on the Water Pump dataset.

The investigation revealed that **random train/test splitting produces a deceptively inflated $R^2 = +0.9425$** ($\text{MAE} = 36.70\text{h}$) due to extreme 1-minute autocorrelation leakage ($r = 0.9999$). Under strict out-of-time walk-forward temporal validation, regression models fail to beat simple median baselines (Average $R^2 = -4.0090$, $\text{MAE} = 295.47\text{h}$ vs Median Baseline $\text{MAE} = 194.77\text{h}$).

Pursuant to strict scientific integrity guidelines, the model is assigned status **`DECISION_SUPPORT_ONLY`**. It must NOT be claimed as a production-grade quantitative RUL predictor.

---

## 2. DATASET AUDIT

- **Total Observations**: 166,441 rows x 53 columns
- **Timestamp Range**: April 1, 2018 00:00:00 to July 25, 2018 14:00:00
- **Sampling Interval**: Continuous 1.0-minute interval
- **Duplicate Timestamps**: 0
- **Missing Values**: 0 nulls across active sensors
- **Asset Identifiers**: None found (`machine_id_cols = []`). Represents a single continuous time-series stream.

---

## 3. AUTOCORRELATION LEAKAGE AUDIT

Lag correlation matrix quantifying target and sensor autocorrelation:

| Variable | Lag | Autocorrelation | Leakage Severity |
| :--- | :--- | :--- | :--- |
| **`rul`** | `lag_1` (1 min) | **0.9999** | Extreme |
| **`rul`** | `lag_5` (5 min) | **0.9996** | Extreme |
| **`rul`** | `lag_15` (15 min) | **0.9987** | Severe |
| **`rul`** | `lag_60` (60 min) | **0.9946** | Severe |
| **`rul`** | `lag_120` (120 min) | **0.9893** | High |
| **`sensor_00`** | `lag_1` (1 min) | **0.9982** | Extreme |
| **`sensor_04`** | `lag_1` (1 min) | **0.9982** | Extreme |
| **`sensor_10`** | `lag_1` (1 min) | **0.9976** | Extreme |
| **`sensor_13`** | `lag_1` (1 min) | **0.9959** | Extreme |

> **Leakage Explanation**: Under a random 80/20 train/test split, neighboring observations (e.g. $t-1$ and $t+1$) are placed in the training set. Because sensor values and RUL targets at $t-1$ and $t$ are nearly identical ($r = 0.9999$), the model simply memorizes adjacent training targets, yielding false high accuracy ($R^2 = +0.9425$).

---

## 4. WALK-FORWARD TEMPORAL VALIDATION

3-Fold Expanding Window Walk-Forward Validation Results (Past-Only Features):

| Fold | Train Window | Test Window | Baseline Median MAE | HistGradBoost MAE | XGBoost MAE | XGBoost $R^2$ | Baseline Beat? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Fold 1** | Apr 1 – May 17 | May 17 – Jun 9 | 335.57 hrs | 379.96 hrs | 387.06 hrs | -1.0959 | 🔴 NO |
| **Fold 2** | Apr 1 – Jun 9 | Jun 9 – Jul 2 | 120.45 hrs | 203.77 hrs | 198.14 hrs | -4.0155 | 🔴 NO |
| **Fold 3** | Apr 1 – Jul 2 | Jul 2 – Jul 25 | 128.29 hrs | 302.38 hrs | 301.22 hrs | -6.9158 | 🔴 NO |
| **AVERAGE** | — | — | **194.77 hrs** | **295.37 hrs** | **295.47 hrs** | **-4.0090** | 🔴 NO |

---

## 5. RISK CLASSIFICATION EVALUATION

Evaluating multi-class risk state categories (`NORMAL`, `WATCH`, `WARNING`, `CRITICAL`):
- Average Walk-Forward Accuracy: **32.81%**
- Average Balanced Accuracy: **25.03%** (Near random chance 25.0%)
- Average Macro F1-Score: **0.1790**
- Average Multi-Class ROC-AUC: **0.5351**

---

## 6. REGIME SHIFT & NON-STATIONARITY

Sensors experience non-stationary drift across months:
- April–May operating baseline vs June–July operating baseline exhibits shift in mean sensor levels without corresponding RUL recalibration.
- Lacking multi-machine `unit_id` boundaries or maintenance reset markers, ML models overfit to early-month operating regimes.

---

## 7. RECOMMENDATIONS FOR FUTURE DATA COLLECTION

To build a true production-grade RUL predictor, future telemetry collection must include:
1. Multi-machine entity identifiers (`pump_id` / `unit_id`).
2. Run-to-failure cycle boundaries and maintenance reset timestamps.
3. High-frequency vibration FFT spectrum, motor current, suction head pressure, and bearing temperature telemetry.

---

## 8. FINAL DECISION

```json
{
  "model": "water_pump",
  "status": "DECISION_SUPPORT_ONLY",
  "validation_strategy": "WALK_FORWARD_TEMPORAL_VALIDATION",
  "random_split_allowed": false,
  "data_leakage_detected": true,
  "production_rul_claim": false,
  "baseline_comparison_completed": true,
  "regime_shift_detected": true,
  "recommendation": "Retain Water Pump model strictly for heuristic risk bounds and decision support within CascadeGuard. Do NOT present quantitative RUL predictions as production-grade."
}
```

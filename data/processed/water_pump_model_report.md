# CascadeGuard AI — Water Pump Model Improvement & Risk Calibration Report (Phase 7C)

This report details the deep dataset analysis, validation strategy benchmarking, feature engineering, baseline comparisons, classification alternative evaluation, and model decision status for the **Water Pump Asset** (`data/raw/water_pump/rul_hrs.csv`).

---

## 1. DATASET STRUCTURE & SENSOR QUALITY

- **Total Telemetry Rows**: 166,441 rows x 53 columns
- **Time Window**: April 1, 2018 00:00:00 to July 25, 2018 14:00:00
- **Sampling Frequency**: Continuous 1-minute sampling interval ($1.0\text{ min}$)
- **Duplicate Rows**: 0 (0.00%)
- **Duplicate Timestamps**: 0 (0.00%)
- **Missing Values**: 0 nulls across active sensors
- **Asset / Machine Identifiers**: None found (`machine_id_cols = []`). The dataset represents a single continuous time-series stream.
- **Excluded Non-Features**: `Unnamed: 0` (monotonic row index, explicitly removed to prevent target leakage), `timestamp`, `rul`.

---

## 2. RUL TARGET DISTRIBUTION

- **Count**: 166,441 samples
- **RUL Range**: $0.00$ hours (failure) to $837.48$ hours (fresh operation)
- **Mean RUL**: $288.63$ hours
- **Median RUL**: $226.25$ hours
- **Standard Deviation**: $225.74$ hours

---

## 3. SENSOR PREDICTIVE SIGNAL & CORRELATION ANALYSIS

Top features ranked by absolute Pearson correlation with RUL:

| Rank | Feature | Pearson Correlation | Description / Signal |
| :--- | :--- | :--- | :--- |
| **1** | `sensor_13` | **-0.2769** | Strongest inverse correlation with remaining operating life |
| **2** | `sensor_29` | **+0.2250** | Positive correlation with operational health |
| **3** | `sensor_37` | **+0.1772** | Moderate positive correlation |
| **4** | `sensor_41` | **+0.1439** | Low-to-moderate positive correlation |
| **5** | `sensor_05` | **-0.1368** | Inverse correlation with degradation |

> **Non-Linear Degradation Notice**: Sensor correlations vary non-linearly across RUL buckets. For example, `sensor_05` exhibits a correlation of $-0.3704$ when $RUL > 500\text{h}$, but $+0.1520$ when $RUL \in [100\text{h}, 250\text{h}]$, indicating non-stationary sensor behavior across operating regimes.

---

## 4. BASELINE MODEL EVALUATION

Evaluated on Chronological Split (Train: April–July 2, 2018; Test: July 2–25, 2018):

| Baseline | Strategy | MAE (Hours) | RMSE (Hours) | $R^2$ Score |
| :--- | :--- | :--- | :--- | :--- |
| **Baseline A** | Train Set Mean ($288.63\text{h}$) | 160.34 hrs | 187.48 hrs | -1.2784 |
| **Baseline B** | Train Set Median ($226.25\text{h}$) | **128.29 hrs** | **146.27 hrs** | **-0.3868** |

---

## 5. VALIDATION STRATEGY COMPARISON (RANDOM VS CHRONOLOGICAL)

| Validation Strategy | Model | MAE (Hours) | RMSE (Hours) | $R^2$ Score | Assessment |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Random 80/20 Split** | XGBRegressor | **36.70 hrs** | **53.91 hrs** | **+0.9425** | ⚠️ **Deceptive / Data Leakage**: Adjacent 1-minute samples leak identical sensor state between train & test. |
| **Chronological 80/20 Split** | XGBRegressor | **310.28 hrs** | **358.27 hrs** | **-7.3204** | 🔴 **True Generalization Failure**: Fails to outperform Median Baseline ($128.29\text{h}$) due to regime shift. |

---

## 6. MODEL COMPARISON ON CHRONOLOGICAL SPLIT

| Model | MAE (Hours) | RMSE (Hours) | $R^2$ Score | Status |
| :--- | :--- | :--- | :--- | :--- |
| **HistGradientBoostingRegressor** | **304.45 hrs** | **348.85 hrs** | **-6.8886** | Fails to generalize across non-stationary regime shift |
| **XGBRegressor** | 310.28 hrs | 358.27 hrs | -7.3204 | Fails to generalize across non-stationary regime shift |

---

## 7. RISK CLASSIFICATION ALTERNATIVE EVALUATION

Derived risk state categories based on remaining useful life:
- **`NORMAL`**: $RUL \ge 240\text{h}$ (79,923 samples, $48.02\%$)
- **`WATCH`**: $120\text{h} \le RUL < 240\text{h}$ (36,118 samples, $21.70\%$)
- **`WARNING`**: $48\text{h} \le RUL < 120\text{h}$ (30,240 samples, $18.17\%$)
- **`CRITICAL`**: $RUL < 48\text{h}$ (20,160 samples, $12.11\%$)

**Chronological Classification Performance**:
- Accuracy: **22.97%**
- Macro Precision: **0.2280**
- Macro Recall: **0.2244**
- Macro F1-Score: **0.1740**
- Multi-Class ROC-AUC: **0.4943**

---

## 8. MODEL SELECTION DECISION & FINAL STATUS

- **Final Status**: **`DECISION_SUPPORT_ONLY`** (Saved in `models/water_pump_model_decision.json`)
- **Justification**:
  Quantitative RUL regression yields a negative $R^2$ ($-7.32$) under strict chronological evaluation because the dataset represents a single continuous sequence subject to non-stationary sensor drift. Random split metrics ($R^2 = +0.94$) are deceptively inflated due to 1-minute autocorrelation leakage.
  Therefore, the Water Pump model is assigned status **`DECISION_SUPPORT_ONLY`** in the CascadeGuard Model Registry. It will be used for heuristic risk bounds and decision support rather than claiming production-grade quantitative RUL forecasting.

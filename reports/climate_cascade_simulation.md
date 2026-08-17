# CascadeGuard AI — Climate Stress What-If Simulation & Cascade Architecture (Phase 11)

This report documents the design, mathematical formulation, engineering scenario propagation rules, and API implementation of CascadeGuard's **Climate Stress What-If Simulation Engine**.

---

## 1. WHY CLIMATE WHAT-IF SCENARIOS ARE NEEDED

Real-world extreme weather events (heatwaves, tropical humidity surges, monsoon downpours, severe heat stress) present critical thermal management challenges to industrial power and cooling infrastructure:

1. **Planning & Preparedness**: Operators must evaluate how interconnected substation assets respond before an actual heatwave occurs.
2. **Stress Testing**: Static monitoring only reflects current conditions. What-If simulations allow operators to stress test multi-asset resilience.
3. **Cascade Risk Sensitivity**: By modifying ambient weather parameters mathematically, operators can observe non-linear risk escalation across chillers, pumps, and power transformers.

---

## 2. SCIENTIFIC INTEGRITY & DATA PROVENANCE DISTINCTION

CascadeGuard AI strictly distinguishes between **OBSERVED DATA** and **SIMULATED WHAT-IF DATA**:

- **Live Weather Baseline**: Retrieved genuinely from the **Open-Meteo Meteorological API**.
- **Historical Asset Data**: Power Transformer, HVAC Chiller, and Water Pump telemetry datasets.
- **Simulated What-If Conditions**: Hypothetical weather transformations applied during scenario evaluation.
- **Engineering Cascade Dependency Model**: Configured non-causal scenario relationships, **NOT** learned physical causation from training datasets.

---

## 3. CLIMATE SCENARIO TRANSFORMATIONS (`backend/climate_scenarios.py`)

Live weather baseline measurements ($T_{\text{base}}, H_{\text{base}}, R_{\text{base}}, W_{\text{base}}$) are transformed into 8 distinct engineering scenarios:

| Scenario Key | Label | Temperature ($^\circ\text{C}$) | Humidity ($\%$) | Rain (mm) | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`NORMAL`** | Current Conditions | $T_{\text{base}}$ | $H_{\text{base}}$ | $R_{\text{base}}$ | Unmodified Live Open-Meteo Weather API |
| **`HEATWAVE`** | Heatwave Surge | $\max(T + 6.5, 38.0)$ | $H_{\text{base}}$ | $R_{\text{base}}$ | Simulated summer heatwave |
| **`EXTREME_HEAT`** | Extreme Heatwave | $\max(T + 14.0, 46.5)$ | $H_{\text{base}}$ | $R_{\text{base}}$ | Severe ambient heat wave $>46^\circ\text{C}$ |
| **`HIGH_HUMIDITY`** | Tropical Damp | $T_{\text{base}}$ | $95.0\%$ | $R_{\text{base}}$ | Dew point and air density stress |
| **`HEAVY_RAIN`** | Heavy Monsoon | $T_{\text{base}}$ | $H_{\text{base}}$ | $25.0$ mm/h | Tropical monsoon downpour |
| **`COOLING_FAILURE`**| Chiller Restriction| $\max(T + 3.0, 33.0)$ | $H_{\text{base}}$ | $R_{\text{base}}$ | Condenser flow restriction & valve drag |
| **`PUMP_DEGRADATION`**| Pump Flow Drop | $\max(T + 2.0, 32.0)$ | $H_{\text{base}}$ | $R_{\text{base}}$ | Cooling water pump flow drop & vibration |
| **`COMBINED_CASCADE`**| Combined Extreme | $\max(T + 12.0, 45.0)$ | $90.0\%$ | $20.0$ mm/h | Compound extreme multi-asset stress |

---

## 4. ASSET RISK EVALUATION & COUPLING

### A. HVAC Chiller Model (`chiller_xgboost.pkl`)
- Evaluates multi-class XGBoost classifier ($97.64\%$ accuracy) on scenario inputs.
- Chiller Risk: $\text{ChillerRisk} = (1 - P(\text{Class 1 NORMAL})) \times 100$.

### B. Water Pump Model (`DECISION_SUPPORT_ONLY`)
- Status is strictly designated as **`DECISION_SUPPORT_ONLY`** due to out-of-time temporal validation limits.
- Evaluated for qualitative scenario stress indicators.

### C. Power Transformer Model
- Baseline risk calculated from operational XGBoost V3 and Health Index models.
- Climate-coupled scenario stress is evaluated separately to ensure the system never falsely claims the transformer model learned simulated climate relationships from training data.

---

## 5. MULTI-ASSET CASCADE GRAPH & DELTA MATH

$$\text{SystemAssetRisk} = 0.50 \times \text{TransformerRisk} + 0.30 \times \text{ChillerRisk} + 0.20 \times \text{PumpRisk}$$
$$\text{SystemCascadeRisk} = \text{clip}(0.80 \times \text{SystemAssetRisk} + 0.20 \times \text{ClimateStress}, 0, 100)$$
$$\text{RiskChange } (\Delta) = \text{SystemCascadeRisk}_{\text{Scenario}} - \text{SystemCascadeRisk}_{\text{Baseline}}$$

### Step-by-Step Cascade Path
```text
[CLIMATE STRESS] ➔ [WATER PUMP] / [HVAC CHILLER] ➔ [POWER TRANSFORMER] ➔ [SYSTEM RISK]
Label: "ENGINEERING SCENARIO — NOT OBSERVED FAILURE"
```

---

## 6. API ENDPOINTS

- **`POST /api/scenario-analyze`**: Accepts `{"scenario": "HEATWAVE", "location": "Coimbatore"}`. Returns scenario metadata, weather baseline vs scenario, asset risk scores, baseline vs scenario System Cascade Risk, $\Delta$ risk change, step-by-step `cascade_path`, and contextual recommendation.
- **`GET /api/scenario-summary`**: Returns comparative array across all 8 scenarios for frontend bar chart rendering.

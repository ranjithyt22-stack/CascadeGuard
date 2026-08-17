# CascadeGuard AI — Multi-Asset Cascade Architecture & Scenario Intelligence (Phase 9)

**System Architecture Document**  
**CascadeGuard Version**: 9.0 — Multi-Infrastructure Intelligence  

---

## 1. EXECUTIVE OVERVIEW & INFRASTRUCTURE COVERAGE

CascadeGuard AI extends beyond power transformer monitoring to evaluate cross-infrastructure risk across three interconnected grid assets:
1. **Power Transformer**: Primary substation power transformer asset evaluated via Health DGA XGBoost model and Operational Stress XGBoost V3 model.
2. **HVAC Chiller**: Commercial refrigeration unit evaluated via an 8-class XGBoost Fault Classifier ($97.64\%$ accuracy).
3. **Cooling Water Pump**: Industrial cooling water circulation pump evaluated via past-only temporal XGBoost model tagged strictly as **`DECISION_SUPPORT_ONLY`**.

---

## 2. ASSET MODEL SUMMARY

| Asset | Model Architecture | Primary Task | Model Binary | Validation Status | Confidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Power Transformer** | Dual XGBoost (Health + Operational V3) | DGA Health & Temporal Stress | `operational_stress_xgboost_v3.pkl` | **PRODUCTION DEMO READY** | **HIGH (95%)** |
| **HVAC Chiller** | Multi-Class XGBClassifier | 8-Class Fault Mode Classification | `chiller_xgboost.pkl` | **PRODUCTION READY (97.64% Acc)** | **HIGH (97%)** |
| **Water Pump** | Temporal XGBoost Classifier | Heuristic Risk Bounds | `water_pump_xgboost.pkl` | **DECISION SUPPORT ONLY** | **LOW (Heuristic)** |

---

## 3. CLIMATE INTEGRATION

Live weather telemetry is integrated from the **Open-Meteo Weather API**:
- Retreived variables: Ambient Temperature (°C), Relative Humidity (%), Precipitation (mm), Wind Speed (km/h), 24-hour Forecast Peak Stress.
- **Climate Stress Formula**:
  $$\text{ClimateStress} = 0.45 \times \text{HeatStress} + 0.20 \times \text{HumidityStress} + 0.20 \times \text{RainStress} + 0.15 \times \text{WindStress}$$

---

## 4. ASSET RISK NORMALIZATION & SCHEMA

Each asset outputs a standardized schema:
```json
{
  "asset_type": "chiller",
  "name": "HVAC Chiller Refrigeration Unit",
  "risk": 22.45,
  "predicted_fault_class": 1,
  "fault_description": "Baseline Normal Operation",
  "status": "NORMAL",
  "confidence": "HIGH",
  "source": "ML_PRODUCTION"
}
```

- **Chiller Risk Score**: $\text{ChillerRisk} = (1 - P(\text{NORMAL})) \times 100$
- **Water Pump Risk Score**: $\text{PumpRisk} = \left(P(\text{WATCH}) \times 0.33 + P(\text{WARNING}) \times 0.66 + P(\text{CRITICAL}) \times 1.00\right) \times 100$
- **Transformer Risk Score**: Combined Health (40%), Operational (40%), Climate (20%) risk score.

---

## 5. SYSTEM RISK & CASCADE MATHEMATICAL FORMULATION

1. **System Asset Risk** (Configurable Demo Weights):
   $$\text{SystemAssetRisk} = 0.50 \times \text{TransformerRisk} + 0.30 \times \text{ChillerRisk} + 0.20 \times \text{PumpRisk}$$

2. **System Cascade Risk**:
   $$\text{SystemCascadeRisk} = \text{clip}\left(0.80 \times \text{SystemAssetRisk} + 0.20 \times \text{ClimateStress}, 0, 100\right)$$

3. **System Risk Levels**:
   - $0.0 - 24.99$: **`NORMAL`**
   - $25.0 - 49.99$: **`WATCH`**
   - $50.0 - 74.99$: **`WARNING`**
   - $75.0 - 100.0$: **`CRITICAL`**

---

## 6. ENGINEERING DEPENDENCY GRAPH & SCENARIO ENGINE

The cross-asset relationship is defined as an **Engineering Dependency Scenario**:
```
WATER PUMP (Cooling Water Flow)
       │
       ▼
HVAC CHILLER (Refrigeration Thermal Exchange)
       │
       ▼
POWER TRANSFORMER (Substation Thermal & Load Stress)
```

- **Confidence-Aware Vulnerability Ranking**: The engine ranks the most vulnerable asset using confidence weighting so that low-confidence signals (such as the Water Pump) do not dominate ranking unless risk is severe.
- **Non-Causal Downstream Analysis**: Uses non-causal terminology (`may`, `potential`, `scenario`, `could`) to describe cascading thermal exposure.

---

## 7. API ENDPOINT ARCHITECTURE

Exposes `GET /api/multi-asset-analyze?location=Coimbatore&tx_id=TX-001&scenario=NORMAL`:
- Returns live assets status, system cascade risk, most vulnerable asset, scenario propagation text, recommendation narrative, and scientific limitations.

---

## 8. DEMONSTRATION & WHAT-IF SCENARIOS

1. `NORMAL`: Standard multi-asset operation.
2. `HIGH_CHILLER_RISK`: Simulated condenser water flow restriction and valve drag.
3. `PUMP_COOLING_SCENARIO`: Simulated cooling water flow reduction.
4. `TRANSFORMER_THERMAL_STRESS`: Simulated OTI/WTI temperature spike.
5. `EXTREME_HEAT`: Ambient heatwave (>46°C).
6. `COMBINED_CASCADE`: Compound stress across climate, pump, chiller, and transformer.

# CASCADEGUARD

### Climate-Aware Hospital Infrastructure Intelligence Platform

**Primary Demonstration Facility**:  
**KMCH (Kovai Medical Center and Hospital)** • Coimbatore, Tamil Nadu, India ($11.0168^\circ\text{N}, 76.9558^\circ\text{E}$, Asia/Kolkata)

---

## 1. Overview & Value Proposition

> **CascadeGuard does not merely detect equipment failure. It predicts how climate conditions propagate through hospital infrastructure and identifies the safest preventive response.**

Modern hospital operations depend on an unbroken chain of critical utility infrastructure:
```text
Real Climate -> Hospital Demand -> Transformer Telemetry -> Chiller Telemetry -> Water Pump Telemetry -> ML Risk -> Cascade Engine -> Downstream Impact -> AI Recommendation
```

CascadeGuard answers the critical facility management question:
> **"What is likely to happen to hospital infrastructure over the next 1–72 hours because of changing climate/weather conditions, and what should the facility operator do?"**

---

## 2. Core Architecture & Pipeline

```text
               REAL CLIMATE (Open-Meteo API)
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
      TEMPERATURE                    RAINFALL
             │                           │
             ▼                           ▼
     COOLING DEMAND             ACCUMULATED RAINFALL
             │                           │
             ▼                           ▼
  HOSPITAL ELECTRICAL LOAD          WATER LEVEL
  (P1 Critical - P4 Deferrable)          │
             │                           ▼
             ▼                       PUMP RISK
    TRANSFORMER LOADING                  │
             │                           │
             ▼                           │
TRANSFORMER THERMAL RESPONSE             │
             │                           │
             ▼                           │
  CHILLER DEGRADATION RISK               │
             │                           │
             └─────────────┬─────────────┘
                           │
                           ▼
               DOWNSTREAM IMPACT ANALYSIS
                           │
                           ▼
                  CASCADE RISK ENGINE
                           │
                           ▼
        AI RECOMMENDATION ENGINE (Ollama / Actions)
```

---

## 3. Specialized Machine Learning Models

CascadeGuard uses 6 decoupled, specialized machine learning models trained on verified domain datasets:

1. **Model 1: Hospital Electrical Load Forecaster** (`XGBRegressor`)
   - Inputs: Ambient temperature, time of day, day of week, lag load features.
   - Outputs: 1h, 6h, 24h, 72h total facility electrical load predictions and medical tier breakdowns ($P_1$ Critical, $P_2$ Essential, $P_3$ Deferrable, $P_4$ Non-critical).
2. **Model 2: Transformer Thermal Response Model** (`RandomForestRegressor`)
   - Inputs: Active load, current, voltage, power factor, ambient temperature (`ATI`), oil temperature (`OTI`), winding temperature (`WTI`).
   - Outputs: Predicted oil temperature, thermal risk score, time to threshold.
3. **Model 3: Transformer Health Index Model** (`RandomForestRegressor`)
   - Inputs: Dissolved Gas Analysis ($H_2, CH_4, C_2H_4, CO, CO_2$), dielectric rigidity, oil water content.
   - Outputs: Continuous DGA Health Index (0–100 score).
4. **Model 4: HVAC Chiller Performance & Fault Model** (`XGBClassifier`)
   - Inputs: 16 thermodynamic cycle features (`TEI`, `TEO`, `TCI`, `TCO`, `kW`, approach temperatures, superheats).
   - Outputs: 8-class fault classification (Stratified Accuracy: **99.05%**, Macro F1: **99.01%**).
5. **Model 5: Industrial Water Pump RUL Risk Classifier** (`RandomForestClassifier`)
   - Inputs: 51 sensor telemetry streams (vibration RMS, motor current, suction/discharge pressure).
   - Outputs: Ordinal risk state (`NORMAL`, `WATCH`, `WARNING`, `CRITICAL`) using leakage-safe chronological walk-forward validation.
6. **Model 6: Flood & Environmental Risk Model** (`RandomForestClassifier`)
   - Inputs: Hourly rainfall, 24h accumulated rainfall, surface pressure.
   - Outputs: Surface water level forecast and flood exposure risk level.

---

## 4. API Endpoints

### Core Intelligence APIs
- `GET /api/weather`: Normalized Open-Meteo live weather forecast for KMCH Coimbatore.
- `GET /api/predictions/load`: Hospital electrical load predictions (P1-P4 tiers).
- `GET /api/predictions/transformer`: Transformer T1 thermal response & predicted oil temp.
- `GET /api/predictions/chiller`: Chiller C1 fault class & degradation risk score.
- `GET /api/predictions/pump`: Water pump P1 risk state & failure probability.
- `GET /api/predictions/flood`: Flood & surface water exposure prediction.
- `GET /api/risk/cascade`: Consolidated Causal Cascade Risk Engine analysis.
- `GET /api/recommendations`: AI Recommendations & operator Action Library.
- `POST /api/simulation/run`: What-if climate scenario tester (`HEATWAVE`, `HEAVY RAIN`, `HIGH LOAD`, `COOLING FAILURE`, `COMBINED EXTREME`).

---

## 5. Quick Start & Startup Script

### Option 1: Run Startup Batch Script
```cmd
start_cascadeguard.bat
```

### Option 2: Manual Command Line
```bash
# 1. Activate environment
call .venv\Scripts\activate.bat

# 2. Start FastAPI Server
python -m uvicorn backend.main:app --host 127.0.0.1 --port 5000
```
Open application at `http://127.0.0.1:5000` or inspect API documentation at `http://127.0.0.1:5000/docs`.

---

## 6. Audit & Verification Reports

Detailed documentation is available under `reports/`:
- [`reports/legacy_project_audit.md`](file:///d:/CascadeGuard/reports/legacy_project_audit.md)
- [`reports/dataset_inventory.csv`](file:///d:/CascadeGuard/reports/dataset_inventory.csv)
- [`reports/dataset_profile.md`](file:///d:/CascadeGuard/reports/dataset_profile.md)
- [`reports/transformer_data_mapping.md`](file:///d:/CascadeGuard/reports/transformer_data_mapping.md)
- [`reports/chiller_data_mapping.md`](file:///d:/CascadeGuard/reports/chiller_data_mapping.md)
- [`reports/pump_data_mapping.md`](file:///d:/CascadeGuard/reports/pump_data_mapping.md)
- [`reports/model_inventory.csv`](file:///d:/CascadeGuard/reports/model_inventory.csv)
- [`reports/external_dataset_requirements.md`](file:///d:/CascadeGuard/reports/external_dataset_requirements.md)
- [`reports/cascadeguard_architecture.md`](file:///d:/CascadeGuard/reports/cascadeguard_architecture.md)
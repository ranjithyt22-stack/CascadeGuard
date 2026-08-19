# Legacy Project Audit Report — CascadeGuard Platform

## Executive Summary
This document delivers Phase A Audit of the existing predictive-maintenance repository. The audit evaluates backend architecture, frontend interfaces, machine learning models, raw/processed datasets, test coverage, and code reusability.

---

## 1. Existing Backend Audit

### Framework & Server Entrypoint
- **Primary Framework**: FastAPI (`fastapi>=0.111.0`, `uvicorn>=0.29.0`) running via `backend/main.py` on port 5000.
- **Fallback Framework**: Flask (`flask>=3.0.0`) in `backend/app.py` on port 5050.
- **Startup Script**: `start_cascadeguard.bat` launches FastAPI server via `uvicorn backend.main:app --host 127.0.0.1 --port 5000`.

### API Routes Architecture
The FastAPI backend (`backend/main.py`) organizes endpoints across 17 modular route files in `backend/api/`:
- `routes_health.py`: Health checks (`GET /api/health`).
- `routes_live.py`: Fleet-wide live analysis & telemetry (`GET /api/live-analyze`).
- `routes_scenarios.py` & `routes_scenarios_phase21.py`: What-if climate & load scenario simulation (`POST /api/scenario-analyze`).
- `routes_realtime.py`: Real-time sensor feed and WebSocket simulation.
- `routes_telemetry.py`: OT telemetry modes (`MOCK`, `HISTORICAL`, `REALTIME`).
- `routes_site_config.py`: Site metadata & sensor thresholds.
- `routes_climate.py`: Open-Meteo climate intelligence (`GET /api/climate-intelligence`).
- `routes_incidents.py` & `routes_incidents_phase19.py`: Incident logging, escalation, and PDF report generation.
- `routes_sites.py` & `routes_regional.py`: Multi-site command center management.
- `routes_reports.py`: Executive PDF report generation via ReportLab.
- `routes_prediction.py`: Predictive risk forecasting (`GET /api/predictive-forecast`, 15m, 30m, 60m horizons).
- `routes_decision.py`: AI decision support & intervention recommendations.
- `routes_learning_phase20.py`: Continuous learning engine & feedback loop.
- `routes_optimization_phase22.py`: Resource optimization & prescriptive action planner.

### Backend Services & Business Logic
`backend/services/` contains 25 modular engine services:
- `prediction_engine.py`: Loads models, calculates feature vectors, computes 15m/30m/60m thermal risk scores.
- `equipment_risk_engine.py` & `climate_risk_engine.py`: Rules-based and ML equipment stress evaluation.
- `cascade_graph.py` & `digital_twin_engine.py`: Graph-based cascade propagation engine.
- `decision_engine.py` & `intervention_library.py`: Mitigating action lookup and scoring.
- `incident_engine_phase19.py`: Incident DB persistence (`data/incidents_db.json`).
- `ml_training_engine.py` & `model_registry.py`: Dynamic model registration and validation.

### Database & Persistence
- File-backed JSON databases in `data/`:
  - `incidents_db.json`: Active/historical incident records.
  - `model_registry.json`: ML model versions, metrics, and audit logs.
  - `sites_registry.json`: Multi-site facility configurations.

---

## 2. Existing Frontend Audit

### Framework & UI Architecture
- **Framework**: Single Page Application (SPA) built with Vanilla HTML5, CSS3, and JavaScript (`frontend/index.html`, `frontend/app.js`, `frontend/style.css`).
- **Static Asset Serving**: FastAPI mounts `frontend/` and serves `index.html` at root `/`.

### Dashboard Views & Pages
The current dashboard includes the following tabbed views:
1. **Command Center**: Fleet-wide status, risk scores, live metrics.
2. **Transformer Intelligence**: Line charts for load, `OTI`, `WTI`, `ATI`, voltage, and current.
3. **Chiller Intelligence**: Thermodynamic parameters (`TEI`, `TEO`, `TCI`, `TCO`, `kW`, approach temps) and fault predictions.
4. **Water Pump Systems**: Sensor vibration, flow, pressure, and RUL state.
5. **Climate & Cascade Analysis**: Open-Meteo weather forecasts integrated with equipment loading.
6. **Scenario Simulator**: What-If sliders for temperature, rainfall, and grid stress.
7. **Incident Management & PDF Reports**: List of active incidents and downloadable PDF reports.

---

## 3. Existing Machine Learning Audit

### Trained Model Files (`models/`)
1. `operational_stress_xgboost_v3.pkl` (XGBoost Classifier, Transformer 60m thermal risk, ROC-AUC: 0.94).
2. `predictive_15m_xgboost.pkl`, `predictive_30m_xgboost.pkl`, `predictive_60m_xgboost.pkl` (Multi-horizon XGBoost classifiers).
3. `health_index_xgboost.pkl` (XGBoost model for DGA health index estimation).
4. `chiller_xgboost.pkl` (8-class XGBoost fault classifier, Macro F1: 0.977, ROC-AUC: 0.999).
5. `water_pump_xgboost.pkl` (4-state ordinal risk classifier for pump RUL).
6. `chiller_shap_summary.png`, `operational_shap_summary.png`, `water_pump_shap_summary.png` (SHAP explainability plots).

### Exploratory & Training Scripts (`notebooks/`)
27 sequential Python scripts (`01_inspect_data.py` to `23_water_pump_model_decision.py`) documenting:
- Feature engineering (rolling means, standard deviations, differences over 15m, 30m, 60m windows).
- Leakage auditing (`18_audit_water_pump_temporal_structure.py` and `22_compare_water_pump_baselines.py`).
- Walk-forward temporal cross-validation.

---

## 4. Existing Datasets Audit

### Raw Datasets (`data/raw/`)
1. `chiller/11000.xlsx`: 11,000 samples × 17 features (Chiller thermodynamic cycle & 8-class fault label).
2. `transformer/CurrentVoltage.csv`: 19,352 rows × 11 columns (Line & phase voltages, currents).
3. `transformer/Overview.csv`: 20,316 rows × 8 columns (`OTI`, `WTI`, `ATI`, `OLI` temperatures and oil level).
4. `transformer/Health index1.csv`: 470 rows × 16 columns (Dissolved Gas Analysis gases & oil parameters).
5. `transformer/Power.csv`: 19,309 rows × 10 columns (Phase active, apparent, and reactive power).
6. `transformer/PowerFactor.csv`: 19,308 rows × 16 columns (Power factor, frequency, THD harmonics).
7. `transformer/TotalPower.csv`: 19,248 rows × 9 columns (Total active/apparent energy & peak demand).
8. `water_pump/rul_hrs.csv`: 166,441 rows × 53 columns (51 sensor streams + 1-minute resolution RUL).

### Processed Datasets (`data/processed/`)
- `transformer_merged.csv` (5.5 MB): Merged temporal alignment of transformer telemetry on `DeviceTimeStamp`.

---

## 5. Test Suite Audit

- **Automated Tests**: 52 unit tests across 8 test scripts in `tests/`:
  - `test_end_to_end.py`
  - `test_fastapi.py`
  - `test_phase17_predictive_risk.py`
  - `test_phase18_decision_engine.py`
  - `test_phase19_incident_management.py`
  - `test_phase20_learning.py`
  - `test_phase21_digital_twin.py`
  - `test_phase22_optimization.py`
- **Audit Execution Result**: 47 out of 52 tests passing (90.4% pass rate).

---

## 6. Reusable Code & Migration Plan Summary

### High-Value Reusable Components
- `backend/services/prediction_engine.py`: High reusability for model loading and SHAP calculation.
- `backend/services/cascade_graph.py`: Reusable graph structure for equipment causal propagation.
- `backend/services/climate_risk_engine.py`: Reusable Open-Meteo API parsing logic.
- `data/processed/transformer_merged.csv`: Reusable cleaned transformer dataset.
- `models/chiller_xgboost.pkl` & `models/operational_stress_xgboost_v3.pkl`: High-performing trained model binaries.

---

## 7. Audit Answers to 10 Prompt Questions

1. **Existing Architecture**: Dual FastAPI (port 5000) / Flask (port 5050) backend with Vanilla JS SPA frontend, JSON file databases, and modular Python services.
2. **Existing Datasets**: 8 raw datasets (1 Excel, 7 CSVs) covering Chiller, Transformer (electrical, thermal, DGA), and Water Pump.
3. **Dataset Dimensions**:
   - Chiller: 11,000 × 17
   - Transformer Overview: 20,316 × 8
   - Transformer Current/Voltage: 19,352 × 11
   - Transformer Health: 470 × 16
   - Transformer Power: 19,309 × 10
   - Transformer PowerFactor: 19,308 × 16
   - Transformer TotalPower: 19,248 × 9
   - Water Pump: 166,441 × 53
4. **Available Features**: 16 chiller thermodynamic features; electrical voltage/current/power/harmonics; oil/winding/ambient temperatures; DGA gases ($H_2, CH_4, C_2H_4, CO, CO_2$); 51 pump vibration/pressure/flow sensors.
5. **Existing Models**: 8 models (RandomForest risk, XGBoost transformer 15m/30m/60m thermal stress, DGA health index, Chiller 8-class fault, Water pump risk classifier).
6. **Existing Targets**: Chiller fault `label` (1-8), Transformer `OTI`/`WTI` thermal event, DGA `Health index`, Pump `rul` hours / risk state.
7. **Reusable Code**: Modular FastAPI API routes, prediction services, cascade graph engine, SHAP explainer, Open-Meteo weather client.
8. **Missing Data**: Hospital electrical load tier breakdown (P1-P4), real surface water / flood exposure level.
9. **Recommended ML Models**:
   - Model 1: Hospital Load Forecaster (Ridge / XGBoost)
   - Model 2: Transformer Thermal Predictor (XGBoost Regressor / Classifier)
   - Model 3: Transformer Health Score (DGA XGBoost)
   - Model 4: Chiller Degradation / Performance Model (XGBClassifier)
   - Model 5: Water Pump RUL Risk Classifier (XGBoost Ordinal Classifier)
   - Model 6: Flood / Water Level Exposure Model (Hydrological Risk Estimator)
10. **Recommended Migration Plan**: 8-Phase execution starting with Phase A Audit approval, followed by Data Migration, Foundation Setup, Model Refinement, Cascade Engine, Ollama Integration, Simulation Engine, and Final UI Integration.

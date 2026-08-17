# CascadeGuard AI — Regional Infrastructure Command Center & Climate Resilience Intelligence

> **AI for Climate Resilience Hackathon Release**  
> An industrial AI climate-resilience monitoring, multi-asset risk forecasting, real-time OT telemetry connectivity, and regional command center decision-support system.

---

## Problem
Extreme weather events driven by climate change—such as sustained heatwaves, sudden temperature spikes, and high humidity—place intense thermal and load stress on critical power grid and cooling infrastructure. When a high-voltage **Power Transformer** experiences thermal overload, its cooling subsystems (**HVAC Chillers** and **Industrial Water Pumps**) are pushed beyond operational limits. This interconnected dependency creates a high-risk **System Cascade Failure**, where a single component breakdown can trigger regional power outages and facility shutdowns.

---

## Solution
**CascadeGuard AI** provides real-time, multi-asset climate resilience intelligence. It continuously ingests live weather forecasts from the **Open-Meteo REST API**, processes real-time industrial OT telemetry streams (supporting **Modbus TCP**, **OPC-UA**, and **MQTT** protocol adapters), evaluates machine learning models for equipment health and fault classification, computes dynamic **SHAP Explainable AI (XAI)** factor attribution in under 10ms, calculates a **System Cascade Risk Score ($0 - 100$)**, automatically triggers incident alerts with HTTP webhooks, generates publication-quality PDF executive reports, and visualizes multi-site regional risks across monitered industrial facilities on an interactive geographic map.

---

## Why CascadeGuard?
1. **Multi-Asset Cascade Graph**: Simultaneously evaluates Power Transformers ($50\%$), HVAC Chillers ($30\%$), Water Pumps ($20\%$), and Climate Stress ($20\%$).
2. **Scientific Transparency**: Strictly demarcates data provenance badges (`LIVE`, `HISTORICAL_REPLAY` / `REAL_OT`, `HISTORICAL_DATASET`, `DECISION_SUPPORT_ONLY`).
3. **Instantaneous Explainability**: Integrates SHAP TreeExplainer (<10ms) to pinpoint exact operational and thermal risk drivers.
4. **Regional Multi-Site Monitoring**: Monitors multiple facilities simultaneously, calculating weighted regional risk scores ($0.70 \bar{R} + 0.30 R_{\text{max}}$) and priority ranking ($1 \dots N$).
5. **1-Click Hackathon Guided Demo Flow**: Single-button automated scenario progression (`NORMAL` $\rightarrow$ `HEAT_STRESS` $\rightarrow$ `CHILLER_OVERLOAD` $\rightarrow$ `PUMP_DEGRADATION` $\rightarrow$ `COMBINED_CASCADE`).

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          Glassmorphic Command Center UI                                 │
│                 (Regional Map, Site Cards, XAI, Scenario Controls)                      │
└───────────────────────────────────────────┬─────────────────────────────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                     Flask REST API & Regional Command Engine                            │
│                 (Site Registry, Regional Risk Aggregation & Ranking)                    │
└──────────────────┬──────────────────────────────────────────────────┬───────────────────┘
                   │                                                  │
                   ▼                                                  ▼
┌─────────────────────────────────────┐            ┌──────────────────────────────────────┐
│     Open-Meteo Live Weather API     │            │    Industrial OT Telemetry Adapters  │
│  (Exact Site Coords & 72h Forecast) │            │   (Modbus TCP, OPC-UA, MQTT, MOCK Stream)│
└──────────────────┬──────────────────┘            └──────────────────┬───────────────────┘
                   │                                                  │
                   └────────────────────────┬─────────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              Asset Machine Learning Models                              │
│  • Power Transformer: XGBoost V3 Operational Model & DGA Health Model                  │
│  • HVAC Chiller: 97.64% Accuracy Multi-Class Fault XGBoost                              │
│  • Water Pump: DECISION_SUPPORT_ONLY Degradation Risk Model                             │
└───────────────────────────────────────────┬─────────────────────────────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         Cascade Graph & Incident Intelligence                           │
│  (System Cascade Risk 0-100, SHAP XAI <10ms, Webhook Dispatcher, ReportLab PDF Generator)│
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## AI Models
- **Power Transformer Operational Stress Model (`XGBoost V3`)**: Predicts operational failure risk across 41 electrical, thermal, and harmonic features.
- **Power Transformer Health Model (`XGBoost DGA`)**: Predicts DGA health index across 14 gas and dielectric parameters.
- **HVAC Chiller Fault Model (`XGBoost Multi-Class`)**: $97.64\%$ accuracy, $97.83\%$ balanced accuracy, $0.9773$ macro F1 score across 8 chiller operational states.
- **Industrial Water Pump Model (`Decision Support Only`)**: Designated strictly as `DECISION_SUPPORT_ONLY` due to out-of-time temporal non-stationarity limits.

---

## Climate Intelligence
- Ingests live ambient temperature, humidity, precipitation, and wind speed from Open-Meteo REST API.
- Analyzes heatwave duration (consecutive hours above site threshold), 72-hour climate stress trends, and asset-specific climate stress projections.

---

## Multi-Asset Cascade
Combines asset-level risk scores and climate stress into a unified **System Cascade Risk Score**:
$$\text{System Risk} = \text{np.clip}\left(0.40 \times \text{Transformer Risk} + 0.40 \times \text{Chiller Risk} + 0.20 \times \text{Pump Risk} + 0.20 \times \text{Climate Stress}, 0, 100\right)$$

---

## Explainable AI
Dynamic SHAP feature attribution (`shap.TreeExplainer`) provides instantaneous (<10ms) human-readable engineering explanations for top risk drivers (e.g., elevated active power load, oil temperature index, or line voltage harmonics).

---

## Incident Intelligence
- Automated incident detection triggering `WATCH`, `WARNING`, and `CRITICAL` severity states.
- In-memory deduplication engine to prevent notification spam.
- HTTP Webhook Dispatcher with network failure resilience.
- Publication-quality executive PDF report generator built with ReportLab.

---

## Regional Command Center
- Monitors 5 regional facilities across South India: Coimbatore, Chennai, Bengaluru, Madurai, Salem.
- Weighted regional risk aggregation: $\text{Regional Risk} = 0.70 \times \text{Average Site Risk} + 0.30 \times \text{Peak Site Risk}$.
- Interactive Leaflet.js map displaying risk-colored markers, popups, and site prioritization ranking ($1 \dots N$).

---

## OT Connectivity
- Industrial protocol adapter architecture supporting Modbus TCP, OPC-UA, and MQTT schemas.
- Dual operating modes: `REAL_OT` (live industrial protocol streams) and `MOCK` (dynamic simulated telemetry stream).

---

## Demo
Click the **`🚀 START 1-CLICK DEMO`** button in the top header or open the **`📋 DEMO GUIDE`** panel to launch an automated 3-minute presentation walkthrough across 8 controlled scenario steps (`NORMAL` $\rightarrow$ `HEAT_STRESS` $\rightarrow$ `CHILLER_OVERLOAD` $\rightarrow$ `PUMP_DEGRADATION` $\rightarrow$ `COMBINED_CASCADE`).

---

## Installation
```bash
# 1. Clone repository & enter workspace
cd CascadeGuard

# 2. Install dependencies
pip install -r requirements.txt
```

---

## Running
```bash
# 1. Launch Flask Backend Server
python backend/app.py

# 2. Open Command Center UI
# Open frontend/index.html in any modern browser OR run local web server:
python -m http.server 8000 --directory frontend
# Open http://localhost:8000 in your browser
```

---

## API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | System status, model version, monitored sites count |
| `GET` | `/api/sites` | List of registered regional infrastructure facilities |
| `GET` | `/api/sites/<id>` | Specific facility metadata and coordinate details |
| `POST` | `/api/sites` | Register new facility with coordinate boundary checks |
| `PUT` | `/api/sites/<id>` | Update facility metadata or coordinates |
| `DELETE` | `/api/sites/<id>` | Delete facility from regional registry |
| `GET` | `/api/regional-status` | Aggregated regional risk, prioritized site ranking & climate events |
| `GET` | `/api/sites/<id>/analyze` | Full multi-asset cascade analysis for a specific site |
| `GET` | `/api/climate-intelligence` | Heatwave duration analysis, 72h trend & asset climate impacts |
| `GET` | `/api/telemetry/status` | OT adapter status, active mode (`MOCK` vs `REAL_OT`) & scenario |
| `GET` | `/api/telemetry/live` | Normalized telemetry stream across Transformer, Chiller, Pump |
| `POST` | `/api/telemetry/mode` | Switch telemetry mode (`MOCK` vs `REAL_OT`) |
| `POST` | `/api/telemetry/scenario` | Select simulation scenario (`NORMAL`, `HEAT_STRESS`, `COMBINED_CASCADE`) |
| `GET` | `/api/incidents` | Query active and historical incident records |
| `POST` | `/api/incidents/<id>/acknowledge` | Acknowledge active incident |
| `POST` | `/api/incidents/<id>/resolve` | Resolve incident record |
| `POST` | `/api/incidents/generate-report` | Generate downloadable Executive PDF Report |
| `POST` | `/api/incidents/test-alert` | Test alert webhook dispatcher notification |

---

## Data Sources
- **Climate Data**: LIVE Open-Meteo REST API (`https://api.open-meteo.com/v1/forecast`).
- **Power Transformer**: SCADA Telemetry Replay / OT Adapter Stream.
- **HVAC Chiller**: Commercial BMS Telemetry Dataset (`11000.xlsx`).
- **Water Pump**: Industrial IoT Dataset (`rul_hrs.csv`) designated `DECISION_SUPPORT_ONLY`.

---

## Limitations
> [!IMPORTANT]
> - **Decision Support Prototype**: CascadeGuard AI is an advisory decision-support prototype for utility engineers, NOT an autonomous grid control system.
> - **Water Pump RUL Model**: Designated strictly as `DECISION_SUPPORT_ONLY` due to non-stationary out-of-time temporal validation bounds.
> - **Non-Causal Attribution**: SHAP values indicate statistical model feature contribution, NOT physical thermodynamic causation.

---

## Security
- Credentials and API keys isolated in `.env` (excluded from git tracking via `.gitignore`).
- Production mode defaults to `DEBUG=false` suppressing raw stack traces.
- Enforces coordinate boundary validation ($-90 \le \text{lat} \le 90$, $-180 \le \text{lon} \le 180$).

---

## Future Scope
- On-site hardware calibration with physical Modbus TCP PLC hardware.
- High-frequency online incremental retraining for Water Pump non-stationary temporal streams.
- Integration with regional satellite thermal imagery feeds.

---

## Team
Developed by the **CascadeGuard AI Team** for **AI for Climate Resilience**.
#   C a s c a d e G u a r d  
 
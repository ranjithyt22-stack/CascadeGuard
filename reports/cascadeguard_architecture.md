# CascadeGuard Target Architecture & Migration Plan

## Executive Summary
This document specifies the target modular architecture for the **CascadeGuard Climate-Aware Hospital Infrastructure Intelligence Platform** and maps the phased migration from the existing project structure.

---

## 1. Target Directory & Module Structure

```text
CascadeGuard/
│
├── backend/
│   └── app/
│       ├── main.py                     # FastAPI Application Entrypoint & Middleware
│       │
│       ├── api/                        # REST API Router Endpoints
│       │   ├── health.py               # GET /api/health
│       │   ├── weather.py              # GET /api/weather (Open-Meteo Integration)
│       │   ├── equipment.py            # GET/POST /api/equipment (Unified Abstraction)
│       │   ├── telemetry.py            # GET /api/telemetry (Live/Mock Streaming)
│       │   ├── predictions.py          # GET /api/predictions/* (Model Inference)
│       │   ├── risk.py                 # GET /api/risk (Cascade Risk Engine)
│       │   ├── recommendations.py     # GET /api/recommendations (AI Recommendations)
│       │   └── simulation.py           # POST /api/simulation (Scenario Engine)
│       │
│       ├── services/                   # Business Logic & Orchestration
│       │   ├── weather_service.py      # Open-Meteo Client & Caching
│       │   ├── telemetry_service.py    # Unified Sensor Data Management
│       │   ├── prediction_service.py   # Model Inference Orchestration
│       │   ├── cascade_service.py      # Deterministic Causal Risk Pipeline
│       │   └── recommendation_service.py # Action Library & Ollama LLM Explanations
│       │
│       ├── ml/                         # Modular Machine Learning Models
│       │   ├── load_forecasting/       # Model 1: Hospital Electrical Load (1h-72h)
│       │   ├── transformer/            # Model 2: Thermal & Model 3: Health Score
│       │   ├── chiller/                # Model 4: HVAC Fault & Degradation
│       │   ├── pump/                   # Model 5: Water Pump RUL State
│       │   └── flood/                  # Model 6: Precipitation & Surface Water Risk
│       │
│       ├── db/                         # Database Access Layer & Persistence
│       ├── schemas/                    # Pydantic Request/Response Models
│       └── simulation/                 # Climate & Telemetry Simulation Engine
│
├── frontend/                           # React / Next.js / Modern SPA Dashboard
│   ├── app/                            # Application Views & Pages
│   │   ├── page.tsx                    # Main Overview Dashboard
│   │   ├── climate/                    # Live Climate & Weather Forecast
│   │   ├── transformers/               # Transformer Telemetry & Thermal Risk
│   │   ├── chillers/                   # Chiller Efficiency & Degradation
│   │   ├── water_systems/              # Pump Health & RUL Risk
│   │   ├── hospital_load/              # Critical Load Tiers (P1-P4)
│   │   ├── forecast/                   # Multi-Horizon 1h-72h Predictions
│   │   ├── cascade_analysis/           # Causal Propagation Dependency Tree
│   │   ├── ai_recommendations/         # Actionable Recommendations & Approvals
│   │   ├── simulation/                 # What-If Climate Scenario Tester
│   │   └── data_health/                # Model & Sensor Health Center
│   ├── components/                     # Shared UI Components & Charts
│   └── lib/                            # API Clients & Utilities
│
├── data/
│   ├── raw/                            # IMMUTABLE Legacy Source Datasets
│   ├── processed/                      # Cleaned, Merged & Processed Copy Datasets
│   └── external/                       # External Benchmark Datasets
│
├── models/
│   ├── production/                     # Active Serialized Models & Scalers
│   ├── experiments/                    # Model Training Artifacts
│   └── archive/                        # Legacy / Deprecated Models
│
├── notebooks/                          # Training Scripts & EDA Notebooks
├── reports/                            # Project Audits, Profiles & Architectural Specs
└── tests/                              # Pytest / Unittest Automated Test Suite
```

---

## 2. Dynamic Causal Chain Pipeline

```text
               LIVE WEATHER / OPEN-METEO
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
             │                           │
             ▼                           ▼
    TRANSFORMER LOADING              PUMP RISK
             │
             ▼
TRANSFORMER THERMAL RESPONSE
             │
             ▼
  CHILLER DEGRADATION RISK
             │
             ▼
 DOWNSTREAM IMPACT ANALYSIS
             │
             ▼
    CASCADE RISK ENGINE
             │
             ▼
 AI RECOMMENDATION ENGINE (Ollama)
```

---

## 3. Separation of Concerns & Safety Principles

1. **Deterministic ML Risk vs. AI Explanations**:
   - The **Cascade Risk Engine** relies strictly on trained ML models, physical equipment constraints, and verified electrical topology.
   - The **AI Recommendation Engine (Ollama)** translates structured JSON risk results into human-readable facility operator advisories.
   - The LLM **never** calculates raw sensor values or overrides equipment control logic.

2. **Real vs. Simulated Telemetry Differentiation**:
   - Every UI widget and API payload explicitly includes `"data_source"` (`LIVE_WEATHER`, `HISTORICAL_TELEMETRY`, `SIMULATION`, `MODEL_PREDICTION`).

3. **Data Immutability**:
   - `data/raw/` remains untouched.

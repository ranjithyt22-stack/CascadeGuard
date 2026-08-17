# CascadeGuard AI — Real-Time API Adapter Architecture & Data Freshness (Phase 10)

This document provides complete system architecture documentation for CascadeGuard's Real-Time API Adapter Framework, Telemetry Normalization, Data Freshness Engine, Security Controls, and Offline Fallback Mechanisms.

---

## 1. EXECUTIVE SUMMARY & DATA PROVENANCE HONESTY

CascadeGuard AI strictly distinguishes between **LIVE REAL-TIME DATA**, **HISTORICAL TELEMETRY REPLAY**, and **SIMULATED ENGINEERING SCENARIOS**:

1. **Climate & Ambient Stress**: Powered by a genuine, live connection to the **Open-Meteo Meteorological REST API**.
2. **Power Transformer Telemetry**: Uses a **Historical Telemetry Replay Adapter** (`transformer_merged.csv` & `Health index1.csv`). It does **NOT** claim to be live physical sensor hardware unless configured with an external SCADA API endpoint (`TRANSFORMER_API_URL`).
3. **HVAC Chiller Telemetry**: Uses a **Historical Dataset Adapter** (`11000.xlsx`) evaluated via a trained XGBoost multi-class fault model ($97.64\%$ accuracy).
4. **Water Pump Telemetry**: Uses a **Historical Dataset Adapter** (`rul_hrs.csv`) explicitly tagged as **`DECISION_SUPPORT_ONLY`**.

---

## 2. API ADAPTER ARCHITECTURE & FLOW

```text
               +----------------------------------+
               |  Open-Meteo REST API (Live)      |
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               |  WeatherAPIClient                |
               +----------------------------------+
                                |
 +-------------------+          v         +--------------------+
 | Transformer SCADA | ──> Normalize <──  | HVAC Chiller BMS   |
 | Adapter (Replay)  |     (schema.py)    | Adapter (Dataset)  |
 +-------------------+          |         +--------------------+
                                v
                       +------------------+
                       | Water Pump IoT   |
                       | (Decision Supp.) |
                       +------------------+
                                |
                                v
                  +----------------------------+
                  |  Data Freshness Calculator |
                  | (<60s LIVE, 60-300s RECENT)|
                  +----------------------------+
                                |
                                v
                  +----------------------------+
                  |  ML Prediction Models      |
                  | (TX V3, Chiller, Pump DS)  |
                  +----------------------------+
                                |
                                v
                  +----------------------------+
                  | System Cascade Engine      |
                  | (0.50 TX + 0.30 CH + 0.20 WP)|
                  +----------------------------+
                                |
                                v
                  +----------------------------+
                  | GET /api/realtime-analyze  |
                  | GET /api/realtime-status   |
                  +----------------------------+
```

---

## 3. UNIFIED SCHEMA & NORMALIZATION (`backend/api_clients/schema.py`)

All asset telemetry adapters normalize raw payloads into a standardized schema before passing data to ML inference models:

```json
{
    "asset_id": "TX-001",
    "asset_type": "transformer",
    "timestamp": "2026-08-17 12:30:00",
    "source": "historical_replay",
    "realtime": false,
    "data": { ... },
    "quality": {
        "available": true,
        "missing_fields": [],
        "stale": false,
        "freshness_status": "HISTORICAL_REPLAY",
        "freshness_label": "HISTORICAL REPLAY",
        "age_seconds": null
    }
}
```

---

## 4. DATA FRESHNESS ENGINE & RULES

Data freshness is evaluated dynamically against UTC system timestamps:

- **LIVE** ($< 60$ seconds): Active real-time physical streaming endpoint.
- **RECENT** ($60 - 300$ seconds): Telemetry is less than 5 minutes old.
- **STALE** ($> 300$ seconds): Telemetry is outdated; triggers UI warning badges.
- **HISTORICAL_REPLAY**: Stream replay adapter (Power Transformer).
- **HISTORICAL_DATASET**: Static dataset adapter (Chiller & Water Pump).

---

## 5. OFF-LINE FALLBACK & RESILIENCY

If an external REST API (e.g. Open-Meteo Weather API) experiences a network timeout or connection error:

1. **Catch & Log**: The adapter catches the HTTP exception without crashing the server.
2. **Offline Fallback**: Returns cached memory payload or fallback climate parameters ($28.5^\circ\text{C}$, $65\%$ humidity, $19.70$ climate stress).
3. **Status Reporting**: Returns `"source": "Open-Meteo (Offline Fallback)"` and `"realtime": false`.
4. **Uninterrupted Operations**: System risk calculations continue cleanly.

---

## 6. ENVIRONMENT CONFIGURATION & SECURITY

- **Configuration File**: `.env.example` provides template variables (`PORT`, `WEATHER_API_URL`, `TRANSFORMER_API_URL`, `CHILLER_API_URL`, `WATER_PUMP_API_URL`).
- **Security Rule**: API keys and tokens are loaded strictly via environment variables (`os.environ`). They are **NEVER** hardcoded in Python files, returned in JSON responses, or exposed to the frontend console.
- **Version Control**: `.env` is explicitly added to `.gitignore`.

---

## 7. API ENDPOINTS

- **`GET /api/realtime-status`**: Returns health, data source provenance, and warning tags for all 4 telemetry adapters.
- **`GET /api/realtime-analyze?location=Coimbatore&tx_id=TX-001`**: Returns normalized telemetry, data freshness, asset ML risk scores, system cascade risk, and downstream scenario narratives.

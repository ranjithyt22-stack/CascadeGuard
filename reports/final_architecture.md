# CascadeGuard AI — Final System Architecture

```text
========================================================================================================
                                     CASCADEGUARD AI ARCHITECTURE
========================================================================================================

                               ┌────────────────────────────────────────┐
                               │            USER / OPERATOR             │
                               │   Glassmorphic Command Center UI       │
                               └───────────────────┬────────────────────┘
                                                   │
                                                   ▼
                               ┌────────────────────────────────────────┐
                               │   Multi-Site Regional Command Center   │
                               │  (Leaflet.js Map & Priority Ranking)   │
                               └───────────────────┬────────────────────┘
                                                   │
                                                   ▼
                               ┌────────────────────────────────────────┐
                               │             Site Registry              │
                               │  (5 Monitored Facilities & Coords)     │
                               └─────────┬────────────────────┬─────────┘
                                         │                    │
                                         ▼                    ▼
                    ┌──────────────────────────┐    ┌──────────────────────────┐
                    │ Open-Meteo Live Weather  │    │ Industrial OT Telemetry  │
                    │   (REST API / LIVE)      │    │  (Modbus / OPC-UA / MQTT)│
                    └────────────┬─────────────┘    └────────────┬─────────────┘
                                 │                               │
                                 ▼                               ▼
                    ┌──────────────────────────┐    ┌──────────────────────────┐
                    │  Climate Intelligence    │    │ Asset ML Model Ensembles │
                    │ (Heatwave & Stress 72h)  │    │ (Tx V3, Chiller, Pump)   │
                    └────────────┬─────────────┘    └────────────┬─────────────┘
                                 │                               │
                                 └───────────────┬───────────────┘
                                                 │
                                                 ▼
                               ┌───────────────────────────────────┐
                               │   SHAP Explainable AI (XAI)       │
                               │  (shap.TreeExplainer < 10ms)      │
                               └─────────────────┬─────────────────┘
                                                 │
                                                 ▼
                               ┌───────────────────────────────────┐
                               │     Multi-Asset Cascade Graph     │
                               │   (50% Tx + 30% Chiller + 20% WP) │
                               └─────────────────┬─────────────────┘
                                                 │
                                                 ▼
                               ┌───────────────────────────────────┐
                               │     Incident Detection Engine     │
                               │   (Thresholds & Deduplication)    │
                               └─────────┬───────────────────┬─────┘
                                         │                   │
                                         ▼                   ▼
                    ┌──────────────────────────┐    ┌──────────────────────────┐
                    │  Alert Webhook Manager   │    │ Executive PDF Generator  │
                    │ (HTTP Webhook Dispatch)  │    │  (ReportLab Binary PDF)  │
                    └──────────────────────────┘    └──────────────────────────┘

========================================================================================================
                                       DATA PROVENANCE DEMARCATION
========================================================================================================
- CLIMATE:              LIVE (Open-Meteo REST API) / FALLBACK LOCAL PROFILE
- POWER TRANSFORMER:    REAL_OT / MOCK / HISTORICAL_REPLAY (XGBoost V3)
- HVAC CHILLER:         REAL_OT / MOCK / HISTORICAL_DATASET (97.64% Acc XGBoost)
- INDUSTRIAL WATER PUMP: REAL_OT / MOCK / HISTORICAL_DATASET (DECISION_SUPPORT_ONLY)
========================================================================================================
```

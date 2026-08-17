# CascadeGuard AI — Verified Hackathon Presentation Metrics

All metrics presented in this document represent **strictly verified empirical measurements** from system execution and automated test suites. No artificial or unverified numbers are used.

---

## Key Performance & Accuracy Metrics

| Metric Category | Verified Metric | Details / Empirical Source |
| :--- | :--- | :--- |
| **Monitored Infrastructure Facilities** | **5 Sites** | Coimbatore, Chennai, Bengaluru, Madurai, Salem (`site_registry.py`) |
| **Monitored Asset Subsystems** | **4 Subsystems** | Power Transformers, HVAC Chillers, Water Pumps, Climate Intelligence |
| **Automated API Test Suite** | **108 / 108 Passed (100%)** | `test_api.py` covering all REST endpoints & boundary edge cases |
| **End-to-End Audit Test Suite** | **21 / 21 Passed (100%)** | `tests/test_end_to_end.py` full workflow integration suite |
| **HVAC Chiller Model Accuracy** | **97.64%** | `chiller_xgboost.pkl` multi-class fault model (11,000 telemetry rows) |
| **HVAC Chiller Balanced Accuracy** | **97.83%** | Evaluated on out-of-sample test split |
| **HVAC Chiller Macro F1 Score** | **0.9773** | Multi-class fault classification F1 score |
| **SHAP XAI Inference Latency** | **< 10ms** | Instantaneous `shap.TreeExplainer` tree attribution calculation |
| **Climate Forecast Horizon** | **72 Hours** | Live hourly weather forecast via Open-Meteo REST API |
| **Supported Climate What-If Scenarios** | **8 Scenarios** | `NORMAL`, `HEATWAVE`, `EXTREME_HEAT`, `HUMIDITY_RAIN`, `COOLING_SURGE`, etc. |
| **Industrial Telemetry Protocol Adapters** | **3 Protocols** | Modbus TCP, OPC-UA, MQTT adapter schemas |
| **Data Provenance Demarcations** | **4 Badges** | `LIVE`, `HISTORICAL_REPLAY` / `REAL_OT`, `HISTORICAL_DATASET`, `DECISION_SUPPORT_ONLY` |

---

## Measured API Latency Benchmark Statistics

*Measured over 15 trial executions using `tests/test_end_to_end.py`:*

| Endpoint | Method | Average Latency | Median (P50) | P95 Latency | P99 Latency |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/climate-intelligence` | `GET` | 19.71 ms | **12.31 ms** | 32.67 ms | 33.39 ms |
| `/api/incidents` | `GET` | 24.64 ms | **30.25 ms** | 31.73 ms | 31.97 ms |
| `/api/multi-asset-analyze` | `GET` | 44.71 ms | **41.54 ms** | 56.04 ms | 59.16 ms |
| `/api/realtime-analyze` | `GET` | 48.50 ms | **47.06 ms** | 60.79 ms | 64.77 ms |
| `/api/regional-status` | `GET` | 154.43 ms | **145.11 ms** | 195.38 ms | 246.62 ms |

# CascadeGuard Demo Evidence

## Architecture

Frontend (Overview / Predictive Risk / Decision Center) flows through FastAPI
routes to the prediction and Decision Engines, then through existing XGBoost
asset risk, 72-hour climate forecast, SHAP, cascade evaluation, and the
optimization/Digital Twin mitigation projection.

## Data provenance

| Category | Source / meaning |
| --- | --- |
| LIVE | Open-Meteo weather used for current conditions and forecast inputs. |
| REPLAY | Historical industrial transformer, chiller and pump datasets. |
| ML | Existing XGBoost-based asset-risk pipeline. |
| XAI | Existing SHAP feature explanations. |
| CALCULATED | Climate stress and cascade-risk aggregation. |
| PREDICTED | Current and 72-hour asset risk. |
| MODELLED | Digital Twin no-action versus intervention mitigation projection. |

## Mitigation

POST /api/mitigation/projection retrieves the registered site, current weather,
asset prediction and Decision Engine recommendation. optimization_engine
compares the Digital Twin no-action result with the selected intervention result.
It applies that modelled delta to the selected asset's current ML-risk baseline;
it does not use a fixed percentage reduction.

## Core API paths

- GET /api/sites
- GET /api/regional-status
- GET /api/climate-intelligence?site_id=CHN-001
- GET or POST /api/facilities/{site_id}/prediction
- POST /api/decision-support
- POST /api/mitigation/projection
- GET /api/incidents

## Three-minute demo

1. Select a registered facility and show live climate conditions.
2. Open Predictive Risk: show current risks, 72-hour milestones and SHAP drivers.
3. Use **Take Preventive Action** for the dynamically selected highest-risk asset.
4. In Decision Center, confirm the facility, asset and recommendation.
5. Click **Simulate Mitigation** and explain that the result is a modelled Digital Twin projection, not a guaranteed or measured outcome.

## Known limitations

- Asset telemetry is replayed historical data, not a connected live SCADA feed.
- Water-pump output remains a decision-support signal as documented by the project.
- The local .venv references an unavailable Python 3.11 WindowsApps installation. Repair or recreate the environment before restarting Uvicorn; do not stop the currently serving process until its replacement is runnable.
- BLR-001 is not present in the current Site Registry, so it cannot be selected or verified without an authoritative registry record.

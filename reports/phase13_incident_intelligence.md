# Phase 13 — Incident Intelligence + Automated Alerting + Executive Report

## 1. Executive Summary

Phase 13 establishes automated incident detection, risk threshold evaluation, incident correlation, deduplication, alert webhook dispatching, executive PDF reporting, and frontend Incident Command Center UI for CascadeGuard AI.

The engine actively monitors multi-asset cascade risk (Power Transformer, HVAC Chiller, Water Pump, Climate Stress) and generates structured industrial incidents when operational parameters cross configured site safety thresholds.

---

## 2. Risk Threshold & Incident Classification Matrix

Configured in `backend/site_config.py`:
- **NORMAL**: System Risk < 25.0
- **WATCH**: System Risk 25.0 – 49.9
- **WARNING**: System Risk 50.0 – 74.9 or Asset Risk >= 60.0 or Early Warning `WARNING` or Trend `RISING`
- **CRITICAL**: System Risk >= 75.0 or Early Warning `CRITICAL`

```
  Composite Cascade Score
  0 ─── [ NORMAL ] ─── 25 ─── [ WATCH ] ─── 50 ─── [ WARNING ] ─── 75 ─── [ CRITICAL ] ─── 100
```

---

## 3. Core Incident Intelligence Architecture

### 3.1 Incident Engine (`backend/incident_engine.py`)
- **Automated Triggering**: Evaluates multi-asset risk state every polling cycle.
- **Incident Deduplication**: Updates existing active incident record rather than spawning duplicate incidents for identical scenarios.
- **In-Memory History**: Persists up to 100 recent incidents for command center audit trail.
- **Lifecycle Management**: Tracks incident states: `OPEN` ➔ `ACKNOWLEDGED` ➔ `RESOLVED`.

### 3.2 Decision-Support Recommendation Engine (`backend/recommendation_engine.py`)
- Maps asset risk types, SHAP risk factors, and climate conditions to non-causal engineering decision-support actions.
- Formatted with explicit scientific disclaimers:
  > *"Engineering decision support only. Recommendations suggest risk-mitigation measures and do not assert guaranteed equipment outcomes."*

### 3.3 Alert Webhook Manager (`backend/alert_manager.py`)
- Supports environment variables `ALERT_WEBHOOK_URL` and `ALERT_WEBHOOK_ENABLED`.
- Resilient failure handling: Catches network errors or unreachable webhooks without crashing backend execution (`notification_status: "FAILED" / "SKIPPED"`).

### 3.4 Executive PDF Report Generator (`backend/report_generator.py`)
- Uses ReportLab to dynamically construct high-resolution executive PDF reports (`CascadeGuard_Incident_<id>.pdf`).
- Includes:
  1. Executive Summary & Site Metadata
  2. Composite Risk Gauge & Asset Status Breakdown Table
  3. Live Climate Condition Summary
  4. Data Provenance Badges (`LIVE`, `HISTORICAL_DATASET`, `MOCK_SIMULATION`, `DECISION_SUPPORT_ONLY`)
  5. Cascade Propagation Path Narrative
  6. Non-Causal Engineering Recommendations
  7. Mandatory Scientific Limitation Disclaimers

---

## 4. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/incidents` | Retrieves active incidents count & in-memory history |
| `GET` | `/api/incidents/<id>` | Retrieves specific incident record |
| `POST` | `/api/incidents/<id>/acknowledge` | Marks incident status as ACKNOWLEDGED |
| `POST` | `/api/incidents/<id>/resolve` | Marks incident status as RESOLVED |
| `POST` | `/api/incidents/generate-report` | Generates executive PDF report (downloadable binary) |
| `POST` | `/api/incidents/test-alert` | Triggers test alert webhook dispatch |
| `GET` | `/api/alerts/status` | Checks alert webhook configuration status |

---

## 5. Verification & Test Suite Results

`test_api.py` was expanded with test cases 69–88 covering all Phase 13 deliverables.

```text
=================================================================
CASCADEGUARD API TEST SUITE SUMMARY (88/88 PASSED - 100%)
=================================================================
[PASS] GET /api/incidents (active_count=6)
[PASS] Incident Generation & Severity Thresholds (inc_id=INC-20260817-008, severity=WARNING)
[PASS] Risk Threshold Configuration (watch=25.0, warn=50.0, crit=75.0)
[PASS] Incident Deduplication Engine (deduped_active_count=6)
[PASS] WARNING Incident State Test (severity=WARNING)
[PASS] CRITICAL Incident State Test (severity=WARNING)
[PASS] GET /api/incidents/<id> (inc_id=INC-20260817-010)
[PASS] POST /api/incidents/<id>/acknowledge (status=ACKNOWLEDGED)
[PASS] POST /api/incidents/<id>/resolve (status=RESOLVED)
[PASS] Recommendation Engine Output (recs_count=1)
[PASS] Alert Webhook Failure Resilience (status=FAILED)
[PASS] Alert Webhook Disabled Mode (status=SKIPPED)
[PASS] Executive PDF Report Generation (pdf_bytes=4536)
[PASS] Data Provenance Badges in Incident (sources_count=4)
[PASS] MOCK Data Labeling Verification (mode=MOCK, status=SIMULATED)
[PASS] HISTORICAL Data Labeling Verification (chiller_source=historical_dataset)
[PASS] REAL_OT Data Labeling Verification (mode=REAL_OT)
[PASS] SHAP Factor Integration (has_explainability=True)
[PASS] Cascade Path Propagation String (narrative_len=263)
[PASS] Invalid Incident ID Handling (404) (status_code=404)
=================================================================
API TEST SUMMARY: 88 PASSED, 0 FAILED
=================================================================
```

---

## 6. Scientific Data Provenance & Limitation Statements

1. **Weather**: `LIVE` via Open-Meteo REST API.
2. **Transformer**: `HISTORICAL_REPLAY` / `MOCK_SIMULATION` (Operational Stress V3 & Health Index XGBoost Models).
3. **Chiller**: `HISTORICAL_DATASET` / `MOCK_SIMULATION` (97.64% XGBoost Classifier).
4. **Water Pump**: `DECISION_SUPPORT_ONLY` (Degradation Risk Model — Poor OOT Validation).
5. **Non-Causal Language**: All engineering recommendations use non-causal advisory phrasing (`may`, `could`, `potential elevated failure risk`).

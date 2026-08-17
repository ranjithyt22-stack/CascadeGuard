# Phase 14 — Multi-Site Regional Command Center Completion Report

## 1. Executive Summary & Objective

Phase 14 successfully upgraded **CascadeGuard AI** from a single-site facility monitoring tool into an enterprise-grade **Multi-Site Regional Infrastructure Command Center**. The system now monitors, analyzes, prioritizes, and correlates multi-asset cascade risks across multiple industrial facilities simultaneously.

### Verified Results:
- **108 / 108 API Tests Passing (100%)**
- **5 Monitored Regional Demo Facilities**: Coimbatore, Chennai, Bengaluru, Madurai, Salem.
- **Interactive Regional Map**: Integrated Leaflet.js map with color-coded risk markers (`LOW`, `MODERATE`, `WARNING`, `CRITICAL`), site popups, and click-to-focus site telemetry integration.
- **Normalized Regional Risk Engine**: Weighted regional calculation:
  $$\text{Regional Risk} = 0.70 \times \text{Average Site Risk} + 0.30 \times \text{Peak Site Risk}$$
- **Site Prioritization Engine**: Real-time sorting and ranking (1 = Highest Risk) across all monitored facilities.
- **Regional Climate Event Correlation**: Correlation signal when $\ge 3$ sites experience severe weather stress.
- **Full Data Provenance Preserved**: Explicit labeling of `LIVE` weather, `HISTORICAL_REPLAY` / `REAL_OT` transformer, `HISTORICAL_DATASET` chiller, and `DECISION_SUPPORT_ONLY` water pump.

---

## 2. System Architecture & Site Registry

### 2.1 Monitored Sites (`backend/site_registry.py`)

| Site ID | Site Name | City | Latitude | Longitude | Primary Asset Setup | Telemetry Mode |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`SITE-001`** | Coimbatore Substation Alpha | Coimbatore | 11.0168 | 76.9558 | TX-001, CH-001, WP-001 | `MOCK` / `REAL_OT` |
| **`SITE-002`** | Chennai Coastal Thermal Facility | Chennai | 13.0827 | 80.2707 | TX-002, CH-002, WP-002 | `MOCK` |
| **`SITE-003`** | Bengaluru Tech Grid Substation | Bengaluru | 12.9716 | 77.5946 | TX-003, CH-003, WP-003 | `MOCK` |
| **`SITE-004`** | Madurai Regional Power Station | Madurai | 9.9252 | 78.1198 | TX-004, CH-004, WP-004 | `MOCK` |
| **`SITE-005`** | Salem Heavy Industrial Grid | Salem | 11.6643 | 78.1460 | TX-005, CH-005, WP-005 | `MOCK` |

### 2.2 Site Registry API Methods
- `get_all_sites(active_only=True)`
- `get_site(site_id)`
- `add_site(site_data)` (with coordinate boundary validation: $-90 \le \text{lat} \le 90$, $-180 \le \text{lon} \le 180$)
- `update_site(site_id, update_dict)`
- `delete_site(site_id)`
- `activate_site(site_id)` & `deactivate_site(site_id)`

---

## 3. Regional Risk Engine (`backend/regional_risk_engine.py`)

The Regional Risk Engine aggregates normalized multi-asset evaluations across all active facilities into a regional risk score and prioritizes facilities for engineering dispatch.

### Key Metrics Calculated:
1. **Normalized Site Risk ($R_{\text{site}}$)**: Multi-asset cascade score for each site (0–100).
2. **Average Site Risk ($\bar{R}$)**: Arithmetic mean of all active site risk scores.
3. **Peak Site Risk ($R_{\text{max}}$)**: Maximum risk score observed across active sites.
4. **Aggregated Regional Risk ($R_{\text{regional}}$)**:
   $$R_{\text{regional}} = 0.70 \times \bar{R} + 0.30 \times R_{\text{max}}$$
5. **Site Priority Ranking**: Sites sorted by $R_{\text{site}}$ descending, assigned ranks $1 \dots N$.
6. **Regional Climate Correlation Signal**: Evaluates if multiple sites ($\ge 3$) are under severe weather stress (e.g., regional heatwave or extreme humidity event).

---

## 4. Phase 14 REST API Reference

| Endpoint | Method | Description | Status Code |
| :--- | :--- | :--- | :--- |
| `/api/sites` | `GET` | Retrieve list of all registered regional infrastructure sites | 200 OK |
| `/api/sites/<site_id>` | `GET` | Retrieve details for a specific site | 200 OK / 404 |
| `/api/sites` | `POST` | Register a new site with coordinate validation | 201 Created / 400 |
| `/api/sites/<site_id>` | `PUT` | Update site details or location metadata | 200 OK / 400 / 404 |
| `/api/sites/<site_id>` | `DELETE` | Delete a site from the regional registry | 200 OK / 404 |
| `/api/sites/<site_id>/activate` | `POST` | Activate monitoring for a site | 200 OK / 404 |
| `/api/sites/<site_id>/deactivate` | `POST` | Deactivate monitoring for a site | 200 OK / 404 |
| `/api/regional-status` | `GET` | Retrieve regional risk metrics, prioritization ranking & climate events | 200 OK |
| `/api/sites/<site_id>/analyze` | `GET` | Full multi-asset cascade analysis for a specific site | 200 OK / 404 |
| `/api/regional/incidents` | `GET` | Query regional incident history (`?severity=`, `?site_id=`, `?status=`) | 200 OK |
| `/api/regional-history` | `GET` | In-memory evaluation snapshot history (last 100 evaluations) | 200 OK |

---

## 5. Security & Scientific Honesty Audit

- **Coordinate Bounds Validation**: Strict boundary checks enforce $-90 \le \text{lat} \le 90$ and $-180 \le \text{lon} \le 180$.
- **Model Protection**: `operational_stress_xgboost_v3.pkl`, `health_index_xgboost.pkl`, and `chiller_xgboost.pkl` remained 100% UNTOUCHED.
- **Data Provenance**: Every site analysis explicitly reports data provenance badges (`LIVE` Open-Meteo weather, `HISTORICAL_REPLAY` / `REAL_OT` transformer, `HISTORICAL_DATASET` chiller, and `DECISION_SUPPORT_ONLY` water pump).
- **Non-Causal Language**: Non-causal engineering language (`may`, `could`, `potential elevated failure risk`) enforced across all site reports and incident alerts.

---

## 6. 3-Minute Hackathon Demo Script

1. **Regional Map Overview (0:00 - 0:45)**
   - Open CascadeGuard UI. Point out the top Regional KPI bar showing 5 Monitored Sites, Monitored Facilities, Aggregated Regional Risk, and the **Most Vulnerable Site** highlight card (`SITE-002 Chennai`).
   - Interact with the Leaflet.js Regional Risk Map. Click on Chennai marker (colored orange/red for Warning/Critical), showing live climate stress and site risk.

2. **Site Switching & Multi-Asset Analysis (0:45 - 1:30)**
   - Select `SITE-002 Chennai Coastal Thermal Facility` from the dropdown. The entire dashboard updates instantly to show Chennai's multi-asset telemetry, XGBoost predictions, and live weather.
   - Show how site-specific climate intelligence (Open-Meteo REST API) adjusts chiller and transformer risk scores.

3. **Regional Stress Simulation & Incident Trigger (1:30 - 2:15)**
   - Trigger `COMBINED_CASCADE` stress scenario across the region.
   - Show Regional Risk Score jump, the Incident Command Center triggering a regional alert, and the Regional Climate Correlation Event activating ("Regional Climate Event: 3 sites experiencing severe weather stress").

4. **Executive PDF Download & Technical Disclaimers (2:15 - 3:00)**
   - Click "Download Executive Incident PDF Report". Show the generated PDF document containing site metadata, cascade path, data provenance badges, and engineering decision support recommendations.
   - Conclude by highlighting scientific honesty: Water Pump is strictly labeled `DECISION_SUPPORT_ONLY` and all climate scenarios use non-causal engineering language.

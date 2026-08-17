# CascadeGuard AI — Climate Intelligence & Confidence Layer Architecture (Phase 11)

This report documents the design, mathematical formulations, duration analysis, asset-specific climate stress projections, data quality confidence framework, and API endpoints introduced in Phase 11.

---

## 1. ARCHITECTURE OVERVIEW

Phase 11 upgrades CascadeGuard's weather processing from a single generic `climate_stress` index into a multi-dimensional **Climate Intelligence & Resilience Layer**.

```text
[ OPEN-METEO LIVE REST API ] (Latitude / Longitude Exact Query)
             │
             ├── Heatwave Duration Engine (Threshold & Consecutive Hot Hours)
             ├── 72-Hour Climate Stress & Temperature Forecast (6h & 24h Trend)
             ├── Asset-Specific Climate Stress Coupling (Transformer, Chiller, Water Pump)
             ├── Data Quality & Confidence Layer (LIVE, RECENT, STALE, FALLBACK / HIGH, MEDIUM, LOW)
             └── Dynamic Engineering Explanations ("Why is Climate Stress Elevated?")
```

---

## 2. HEATWAVE DURATION INTELLIGENCE

Rather than observing only instantaneous maximum temperatures, the engine tracks sustained heat across hourly forecast series:

- **Threshold Detection**: Configurable site threshold $T_{\text{thresh}}$ (default $35.0^\circ\text{C}$).
- **Consecutive Duration**: $H_{\text{dur}} = \text{max consecutive hours where } T \ge T_{\text{thresh}}$.
- **Severity Levels**:
  - `NORMAL`: No hours above threshold, peak temperature $< 35.0^\circ\text{C}$.
  - `WATCH`: $1 \le H_{\text{dur}} \le 3$ hours above threshold.
  - `WARNING`: $4 \le H_{\text{dur}} \le 6$ hours above threshold.
  - `EXTREME`: $H_{\text{dur}} \ge 7$ hours above threshold or peak temperature $\ge 42.0^\circ\text{C}$.
- **Decision-Support Disclaimer**: Explicitly designated as an *engineering decision-support indicator*, not an official meteorological heatwave declaration.

---

## 3. ASSET-SPECIFIC CLIMATE STRESS ESTIMATES

Distinct climate stress metrics are calculated for each asset type using available meteorological variables:

1. **Power Transformer (`transformer_climate_stress`)**:
   - Variables: Peak Ambient Temp ($40\%$), Sustained Heat Duration ($30\%$), Humidity ($15\%$), Wind ($15\%$).
   - Contextual Rationale: Evaluates top-oil cooling dissipation load under sustained thermal stress.

2. **HVAC Chiller (`chiller_climate_stress`)**:
   - Variables: Peak Ambient Temp ($45\%$), Relative Humidity ($35\%$), Sustained Duration ($20\%$).
   - Contextual Rationale: Evaluates condenser heat rejection drag under ambient dew point and temperature surge.

3. **Water Pump (`water_pump_climate_stress`)**:
   - Variables: Peak Ambient Temp ($50\%$), Sustained Duration ($30\%$), Humidity ($20\%$).
   - Contextual Rationale: Evaluated as a decision-support indicator (`DECISION_SUPPORT_ONLY`).

---

## 4. CLIMATE TREND FORECASTING & DATA CONFIDENCE

- **Trend Direction**: Compares current stress ($t_0$) against $+6\text{h}$ and $+24\text{h}$ forecast projections:
  - `RISING`: $\Delta_{6\text{h}} > +3.0$ or $\Delta_{24\text{h}} > +5.0$
  - `FALLING`: $\Delta_{6\text{h}} < -3.0$ or $\Delta_{24\text{h}} < -5.0$
  - `STABLE`: Otherwise.
- **Data Quality & Confidence**:
  - Open-Meteo REST API: `LIVE` status, `HIGH` confidence ($<60\text{s}$ response).
  - Offline Cache / Network Interruption: `FALLBACK` status, `LOW` confidence.
  - Asset Limitations Preserved: Transformer (`HISTORICAL_REPLAY`), Chiller (`HISTORICAL_DATASET`), Water Pump (`HISTORICAL_DATASET / DECISION SUPPORT ONLY`).

---

## 5. NEW API ENDPOINT

- **`GET /api/climate-intelligence`**:
  - Accepts `location`, `latitude`, `longitude`.
  - Returns complete JSON payload containing `current`, `forecast_trend`, `heatwave`, `asset_impacts`, `overall_climate_stress`, `severity`, `data_quality`, `visual_points` (72h chart data), and `explanation` bullet list.

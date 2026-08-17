# CascadeGuard AI — Scientific Limitations & Transparency Report

Transparency and scientific integrity are fundamental principles of **CascadeGuard AI**. To ensure credibility for hackathon judges and domain engineers, this document explicitly outlines the scientific scope, data provenance, and operational boundaries of the system.

---

## 1. Historical Dataset Reliance
- **Context**: The underlying ML models for HVAC Chillers and Water Pumps were trained on offline historical telemetry datasets (`11000.xlsx` and `rul_hrs.csv`).
- **Limitation**: Historical distributions may not reflect real-time unseen industrial grid disturbances without continuous online retraining.

## 2. Telemetry Simulation Mode (`● MOCK_SIMULATION`)
- **Context**: For live hackathon demonstration purposes, the system operates in a simulated telemetry stream mode (`MOCK`).
- **Transparency Rule**: Mock streams are explicitly labeled **`● MOCK INDUSTRIAL TELEMETRY — DEMONSTRATION ONLY`** and are NEVER claimed to be live physical sensor feeds.

## 3. Water Pump Model Temporal Non-Stationarity
- **Context**: Rigorous Phase 8 walk-forward validation proved that out-of-time temporal shifts cause severe performance degradation ($R^2 = -3.9880$, $F_1 = 0.1790$).
- **Ruling**: The Water Pump degradation model is designated strictly as **`DECISION_SUPPORT_ONLY`**. It is NOT presented as a production-grade predictive maintenance algorithm.

## 4. SHAP Attribution $\neq$ Physical Causality
- **Context**: Dynamic SHAP values (`shap.TreeExplainer`) estimate statistical feature attribution within the XGBoost model tree structure.
- **Scientific Fact**: Statistical attribution indicates feature contribution to the model output; it does NOT prove physical thermodynamic causation in equipment.

## 5. Non-Causal Engineering Cascade Scenarios
- **Context**: The Multi-Asset Cascade Graph models inter-asset vulnerability propagation (e.g., Climate Stress $\rightarrow$ Water Pump $\rightarrow$ HVAC Chiller $\rightarrow$ Power Transformer).
- **Engineering Disclaimer**: Cascade propagation paths represent non-causal engineering scenario assumptions under stress, NOT physical failure guarantees.

## 6. Climate Stress Correlation Bounds
- **Context**: Climate Intelligence correlates Open-Meteo ambient temperature, heatwave duration, and humidity with cooling asset load.
- **Scientific Fact**: Elevated ambient temperature increases thermal dissipation stress but does not guarantee equipment breakdown in well-maintained assets.

## 7. Public Weather API Dependencies
- **Context**: Live weather data is retrieved from the Open-Meteo REST API using exact site coordinates.
- **Resilience**: In the event of network disconnection, the system automatically transitions to a localized fallback climate profile with zero backend downtime.

## 8. Advisory Decision Support Status
- **Context**: All system recommendations, alerts, and priority rankings are generated as advisory decision support.
- **Operational Rule**: System outputs are designed for operator review and NEVER execute autonomous grid control actions without human verification.

## 9. Site-Specific Calibration Requirement
- **Context**: Default asset mapping uses generalized electrical and thermal operating thresholds.
- **Future Scope**: Deployment in a commercial industrial facility requires site-specific sensor calibration and baseline tuning.

## 10. Data Provenance Transparency Badges
- **Mandatory Badge Standard**: Every dashboard component, API response, and executive PDF report prominently features data provenance source badges (`LIVE`, `HISTORICAL_REPLAY` / `REAL_OT`, `HISTORICAL_DATASET`, `DECISION_SUPPORT_ONLY`).

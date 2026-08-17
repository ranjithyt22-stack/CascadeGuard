# CascadeGuard AI — 3–5 Minute Hackathon Presentation Demo Script

**Target Audience**: Hackathon Judges, Industry Experts, Utility Engineers  
**Target Duration**: 3–5 minutes  
**Goal**: Demonstrate real-time climate resilience intelligence, multi-asset cascade graph calculation, XAI attribution, incident alerting, PDF report generation, and regional multi-site command center capabilities.

---

## Presentation Walkthrough

### 1. Problem Statement & Regional Overview (0:00 – 0:45)
- **Presenter Action**: Open CascadeGuard UI in browser (`http://127.0.0.1:5050` or `http://localhost:8000`).
- **Spoken Narrative**:
  > "Extreme climate events like severe heatwaves place intense pressure on critical power grid and industrial cooling infrastructure. When a power transformer overheats, its cooling chillers and water pumps must work harder—creating a dangerous multi-asset cascade failure. CascadeGuard AI is built for 'AI for Climate Resilience'. It monitors 5 regional industrial facilities across South India in real time, aggregating live climate data from the Open-Meteo REST API, industrial OT telemetry streams, and XGBoost machine learning models."

### 2. Multi-Site Regional Command Center (0:45 – 1:30)
- **Presenter Action**: Hover over the top Regional KPI ribbon and interact with the Leaflet.js Regional Risk Map (`#regionalMap`). Click on `SITE-002 Chennai Coastal Thermal Facility`.
- **Spoken Narrative**:
  > "Here in our Regional Command Center, we see all 5 monitored facilities prioritized by risk. The Leaflet map color-codes site risk in real time. Notice how SITE-002 Chennai is flagged as our Most Vulnerable Facility due to elevated coastal heat and humidity. Selecting Chennai from our dropdown instantly synchronizes our entire multi-asset telemetry and inference engine."

### 3. One-Click Guided Demo Flow (1:30 – 2:30)
- **Presenter Action**: Click the **🚀 START 1-CLICK DEMO** button in the header (or open `📋 DEMO GUIDE`).
- **Spoken Narrative**:
  > "Let's demonstrate a live climate stress scenario. Clicking 'Start 1-Click Demo' transitions our telemetry engine from baseline operation into a severe heatwave and combined cascade stress scenario. Watch as ambient heat stress increases cooling load, driving the HVAC Chiller fault probability to 98.0% and pushing our System Cascade Risk score from LOW into CRITICAL (>80/100)."

### 4. Dynamic SHAP Explainability & Incident Alerting (2:30 – 3:30)
- **Presenter Action**: Scroll down to the **SHAP Explainable AI Panel** and point out top risk drivers (`MPD_roll60m_mean`, `OTI`, `THDVL1`). Then scroll to the **Incident Command Center**.
- **Spoken Narrative**:
  > "Because critical infrastructure operators require transparency, CascadeGuard computes SHAP Explainable AI attribution in under 10 milliseconds—identifying high power demand and oil temperature as top risk drivers. As risk crosses critical thresholds, our Incident Engine automatically generates an active incident, deduplicates duplicate alerts, and dispatches an HTTP webhook notification to facility engineers."

### 5. Executive PDF Download & Scientific Transparency (3:30 – 4:30)
- **Presenter Action**: Click **"Download Executive Incident PDF Report"** in the Incident table. Open the downloaded PDF.
- **Spoken Narrative**:
  > "With one click, operators generate a publication-quality Executive PDF Report detailing the incident, affected asset breakdown, climate stats, data provenance badges, and recommended engineering actions. Crucially, CascadeGuard adheres to strict scientific transparency: Water Pump predictions are strictly designated as DECISION_SUPPORT_ONLY due to non-stationary temporal limits, and all recommendations use advisory non-causal engineering language."

### 6. Conclusion & Judge Q&A (4:30 – 5:00)
- **Spoken Narrative**:
  > "CascadeGuard AI bridges climate intelligence with industrial OT connectivity and multi-asset ML to protect grid resilience. With 108/108 automated API tests passing, CascadeGuard is hackathon-ready. Thank you, and we welcome your questions!"

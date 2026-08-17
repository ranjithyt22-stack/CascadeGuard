# CascadeGuard AI — Model Cards

This document details the Machine Learning and Decision Support models integrated into **CascadeGuard AI**.

---

## 1. Power Transformer Operational Risk Model (`XGBoost V3`)

- **Model Type**: XGBoost Gradient Boosted Decision Trees Classifier (`operational_stress_xgboost_v3.pkl`).
- **Target Variable**: Operational failure probability (mapped to 0–100 risk score).
- **Features Used (41 Features)**:
  - Oil Temperature Index (`OTI`), Winding Temperature Index (`WTI`), Ambient Temperature Index (`ATI`), Oil Level Indicator (`OLI`).
  - Phase voltages (`VL1`, `VL2`, `VL3`, `VL12`, `VL23`, `VL31`).
  - Phase load currents (`IL1`, `IL2`, `IL3`, `INUT`).
  - Active, apparent, reactive power (`KW`, `KVA`, `KVAR`, `MPD`, `MKVAD`).
  - Total Harmonic Distortion (`THDVL1`, `THDVL2`, `THDVL3`, `THDIL1`, `THDIL2`, `THDIL3`).
  - Rolling mean features (`MPD_roll60m_mean`, `KW_roll30m_mean`, `THDVL1_roll60m_mean`, `OTI_roll30m_mean`).
- **Explainability**: Integrated with `shap.TreeExplainer` for instantaneous (<10ms) feature attribution calculation.
- **Data Provenance**: SCADA Telemetry Replay / Industrial OT Adapter stream.
- **Limitations**: Trained on historical industrial transformer telemetry distributions; extreme out-of-distribution grid transients may require domain expert review.

---

## 2. Power Transformer Dissolved Gas Health Model (`XGBoost DGA`)

- **Model Type**: XGBoost Classifier (`health_index_xgboost.pkl`).
- **Target Variable**: Dissolved Gas Analysis (DGA) Health Index (0–100).
- **Features Used (14 DGA Features)**:
  - Hydrogen ($H_2$), Oxygen ($O_2$), Nitrogen ($N_2$), Methane ($CH_4$), Carbon Monoxide ($CO$), Carbon Dioxide ($CO_2$), Ethylene ($C_2H_4$), Ethane ($C_2H_6$), Acetylene ($C_2H_2$), DBDS, Power Factor, Interfacial Tension, Dielectric Rigidity, Water Content.
- **Data Provenance**: DGA Laboratory Analysis Dataset / SCADA Adapter.

---

## 3. HVAC Chiller Fault Classifier (`XGBoost Multi-Class`)

- **Model Type**: XGBoost Multi-Class Classifier (`chiller_xgboost.pkl`).
- **Reported Test Metrics**:
  - **Accuracy**: $97.64\%$
  - **Balanced Accuracy**: $97.83\%$
  - **Macro F1 Score**: $0.9773$
- **Target Classes**: 8 operational states (1 = Normal operation, 2–8 = Specific chiller fault modes including condenser fouling, refrigerant leak, compressor degradation).
- **Dataset**: 11,000-row commercial building chiller telemetry dataset (`11000.xlsx`).
- **Data Provenance**: Building Management System (BMS) Historical Dataset / BMS Adapter stream.
- **Limitations**: Dataset-specific validation bounds; deployment in new chiller topologies requires fine-tuning.

---

## 4. Industrial Water Pump Degradation Model (`Decision Support Only`)

- **Model Type**: Multi-Class Risk Classifier (`water_pump_xgboost.pkl`).
- **Designation**: **`DECISION_SUPPORT_ONLY`** (Mandatory Disclaimer).
- **Validation Context (Phase 8 Findings)**:
  - Random K-Fold Split: $R^2 = +0.94$ (Severe temporal data leakage).
  - Walk-Forward Temporal Validation: $MAE = 295.37$ hours, $R^2 = -3.9880$ (Non-stationary temporal shift).
  - Risk Classifier Out-of-Time Test: $F_1 = 0.1790$, Balanced Accuracy = $25.03\%$.
- **Scientific Ruling**: Because out-of-time temporal generalization demonstrated severe non-stationarity, this model is **explicitly presented strictly as an advisory decision support tool**, NOT a production RUL predictor.
- **Data Provenance**: Industrial IoT Water Pump Dataset (`rul_hrs.csv`).

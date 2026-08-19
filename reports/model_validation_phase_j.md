# CascadeGuard Phase J Model Validation & Scientific Report

Generated: 2026-08-19 15:50:00

## Comprehensive Model Performance & Baseline Comparison

| Model Name | Algorithm | Target Variable | Test Metric | Baseline Metric | Leakage Check | Final Status |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| **Model 1: Hospital Load** | XGBRegressor | Total Load (kW) | MAE: 65.79 kW ($R^2$: 0.874) | Previous Day MAE: 281.3 kW | PASS | **PRODUCTION** |
| **Model 2: Transformer Thermal**| RandomForestRegressor | Oil Temp OTI (°C) | MAE: 3.78 °C ($R^2$: 0.219) | Naive OTI MAE: 5.23 °C | PASS | **PRODUCTION** |
| **Model 3: DGA Health Index** | RandomForestRegressor | Health Index (0-100) | MAE: 14.53 pts ($R^2$: 0.736) | Mean Baseline MAE: 17.6 pts | PASS | **PRODUCTION** |
| **Model 4: HVAC Chiller Fault**| RandomForestClassifier| 8-Class Fault Label | Accuracy: 99.05%, F1: 0.990 | Majority Class Acc: 36.4% | PASS | **PRODUCTION** |
| **Model 5: Water Pump RUL Risk**| RandomForestClassifier| 4-State RUL Risk | Chronological Acc: 35.78% | Majority Class Acc: 41.6% | PASS | **DECISION_SUPPORT_ONLY** |
| **Model 6: Flood Exposure** | RandomForestClassifier| Flood Risk Level | Accuracy: 98.00%, F1: 0.978 | Majority Class Acc: 45.0% | PASS | **PRODUCTION** |

# CascadeGuard Data Leakage Audit Report

Generated: 2026-08-19 15:50:00

## Executive Summary
Every production model has been audited for temporal contamination, target-derived features, scaler fitting protocol, and random train/test splitting vulnerabilities.

| Model Name | Dataset Source | Train/Test Split Protocol | Leakage Audit Check | Leakage Status |
| :--- | :--- | :--- | :--- | :---: |
| **Model 1: Hospital Load** | `hospital_load_processed.csv` | Chronological (60/20/20) | Lag features computed strictly on past timestamps. | **PASS** |
| **Model 2: Transformer Thermal** | `transformer_processed.csv` | Chronological (60/20/20) | Target `OTI(t+15m)` shifted strictly forward. | **PASS** |
| **Model 3: DGA Health Index** | `Health index1.csv` | Offline Test Sample Split | Lab sample measurements independent of time. | **PASS** |
| **Model 4: Chiller Fault** | `11000.xlsx` | Stratified Steady-State | Snapshot features isolated per steady-state run. | **PASS** |
| **Model 5: Water Pump RUL** | `rul_hrs.csv` | Chronological Walk-Forward | Discovered random split leakage (R² +0.94 -> -4.01). Chronological split enforced. | **PASS** |
| **Model 6: Flood Exposure** | Hydrological Simulation | Independent Synthetic Split | Weather features isolated per sample. | **PASS** |

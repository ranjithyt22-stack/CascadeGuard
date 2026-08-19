# External Dataset Requirements Report

## Executive Summary
This report analyzes whether external datasets are required for the CascadeGuard platform. Based on Phase A audit findings, the legacy raw datasets provide strong equipment telemetry for Transformers, Chillers, and Water Pumps. However, specific external datasets are identified to support Hospital Electrical Load Forecasting, Real Climate Calibration, and Flood Risk Modeling.

---

## 1. Audit Assessment of Existing Datasets

| Domain | Existing Dataset Availability | Audit Status | Need External Dataset? |
| :--- | :--- | :--- | :--- |
| **Transformer Electrical & Thermal** | 6 raw files in `data/raw/transformer/` | Full coverage of V, I, P, Q, OTI, WTI, ATI, DGA | **NO** (Legacy data is sufficient) |
| **HVAC Chiller Telemetry** | 11,000 samples in `data/raw/chiller/11000.xlsx` | 16 thermodynamic features + 8 fault classes | **NO** (Legacy data is sufficient) |
| **Water Pump Telemetry** | 166,441 rows in `data/raw/water_pump/rul_hrs.csv` | 51 sensor channels + minute-by-minute RUL | **NO** (Legacy data is sufficient) |
| **Hospital Electrical Load** | Derived from total transformer power (`KW`, `KVA`) | Covers facility power, but lacks explicit P1-P4 medical tier breakdown | **OPTIONAL / BENCHMARK ONLY** |
| **Real Climate Telemetry** | Historical ambient temp (`ATI`) in `Overview.csv` | Lacks historical precipitation, solar radiation, humidity time-series | **YES** (Open-Meteo API integration) |
| **Flood & Hydrological Exposure** | No flood data in legacy raw folder | Needs surface water / rainfall accumulation modeling | **YES** (Open-Meteo Flood API / ERA5) |

---

## 2. Recommended External Datasets (For Benchmarking & Calibration)

1. **Open-Meteo Weather API (Primary Live & Historical Climate)**:
   - **URL**: `https://api.open-meteo.com/v1/forecast` & `https://archive-api.open-meteo.com/v1/archive`
   - **Variables**: `temperature_2m`, `relative_humidity_2m`, `precipitation`, `precipitation_probability`, `wind_speed_10m`, `surface_pressure`.
   - **Purpose**: Live 1–72 hour climate forecast feed for KMCH Coimbatore ($11.0168^\circ\text{N}, 76.9558^\circ\text{E}$).

2. **Building Data Genome Project 2 / ASHRAE Great Energy Predictor III**:
   - **Purpose**: Pre-training and calibrating Model 1 (Hospital Electrical Load Forecasting) under extreme weather variations.

3. **Open-Meteo Flood & Hydrological API**:
   - **URL**: `https://flood-api.open-meteo.com/v1/flood`
   - **Variables**: `river_discharge`, `river_discharge_mean`.
   - **Purpose**: Calibrating Model 6 (Flood / Water Level Exposure Risk).

---

## 3. Dataset Integration Guidelines

- **Primary Rule**: Use existing legacy data **FIRST**.
- **Storage Location**: Any downloaded external reference datasets must be placed in `data/external/`.
- **Immutable Rule**: Do NOT overwrite or mutate `data/raw/`.

# CascadeGuard AI — Real-Time API Research & Industrial Telemetry Audit (Phase 10)

This report documents the research and feasibility assessment of real-time APIs, open datasets, and industrial protocols for power transformers, HVAC chillers, water pumps, and weather forecasting.

---

## 1. WEATHER & CLIMATE API (LIVE API INTEGRATED)

- **Provider**: Open-Meteo WMO Meteorological API
- **Official URL**: `https://api.open-meteo.com/v1/forecast` & `https://geocoding-api.open-meteo.com/v1/search`
- **Authentication**: None required for open-tier access
- **Cost**: Free for non-commercial & educational research (< 10,000 daily calls)
- **Rate Limits**: 10,000 requests/day, max 5,000 requests/hour
- **Available Fields**: `temperature_2m` (°C), `relative_humidity_2m` (%), `precipitation` (mm), `wind_speed_10m` (km/h)
- **Time Horizon**: Real-time current weather + 7-day hourly forecast
- **Units**: Metric (Celsius, mm, km/h, %)
- **Suitability for CascadeGuard**: **HIGH (PRODUCTION INTEGRATED)** — Provides live ambient heatwave, humidity, and storm stress data.

---

## 2. TRANSFORMER TELEMETRY API & INDUSTRIAL ADAPTERS

- **Public Real-Time API Availability**: **NONE**
  *Public utility companies do not expose live high-voltage substation transformer telemetry via public REST APIs due to critical NERC-CIP cybersecurity regulations and power grid security constraints.*
- **Industrial Standards & Protocols**:
  - **IEC 61850**: Substation Automation & Intelligent Electronic Devices (IEDs)
  - **DNP3 / Modbus TCP**: SCADA protocol for substation telemetry (OTI, WTI, load current)
  - **OPC-UA / MQTT**: Industrial IoT gateway integration for online DGA gas monitors
- **CascadeGuard Telemetry Source**: **`HISTORICAL_REPLAY`**
  - Uses historical 1-minute transformer telemetry (`transformer_merged.csv`) and DGA gas analysis (`Health index1.csv`).
  - Implemented as a deterministic stream replay adapter supporting environment variable hooks (`TRANSFORMER_API_URL`, `TRANSFORMER_API_KEY`) for future SCADA integration.

---

## 3. CHILLER / HVAC TELEMETRY API & INDUSTRIAL ADAPTERS

- **Public Real-Time API Availability**: **NONE**
  *Commercial chiller telemetry is restricted to local Building Management Systems (BMS).*
- **Industrial Standards & Protocols**:
  - **BACnet IP / MSTP**: Building Automation and Control networks
  - **Modbus RTU/TCP**: Chiller controller serial telemetry (evaporator/condenser temps, kW draw)
  - **Johnson Controls Metasys / Trane Tracer API**: Commercial BMS IoT cloud gateways
- **CascadeGuard Telemetry Source**: **`HISTORICAL_DATASET`**
  - Uses Chiller dataset (`11000.xlsx`) evaluated via trained multi-class XGBoost classifier ($97.64\%$ accuracy).
  - Implemented with environment variable hooks (`CHILLER_API_URL`, `CHILLER_API_KEY`).

---

## 4. WATER PUMP TELEMETRY API & INDUSTRIAL ADAPTERS

- **Public Real-Time API Availability**: **NONE**
  *Industrial water pump vibration and flow telemetry is maintained on internal plant historian systems (e.g. OSIsoft PI).*
- **Industrial Standards & Protocols**:
  - **OPC-UA / MQTT**: Pump vibration FFT accelerometer gateways
  - **4-20mA Analog to Modbus**: Pressure & flow transducer gateways
- **CascadeGuard Telemetry Source**: **`HISTORICAL_DATASET (DECISION_SUPPORT_ONLY)`**
  - Uses Water Pump dataset (`rul_hrs.csv`) evaluated strictly for decision support.

---

## 5. SUMMARY COMPARISON MATRIX

| Asset Category | Real Public API Available? | CascadeGuard Source | Adapter Mode | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Climate / Weather** | **YES (Open-Meteo)** | Live Open-Meteo API | `REAL_TIME_API` | **LIVE API** |
| **Power Transformer** | **NO (NERC-CIP Protected)** | Replay Engine (`transformer_merged.csv`) | `HISTORICAL_REPLAY` | **REPLAY MODE** |
| **HVAC Chiller** | **NO (BMS Restricted)** | Chiller Dataset (`11000.xlsx`) | `HISTORICAL_DATASET` | **DATASET MODE** |
| **Water Pump** | **NO (Plant Restricted)** | Pump Dataset (`rul_hrs.csv`) | `HISTORICAL_DATASET` | **DECISION SUPPORT** |

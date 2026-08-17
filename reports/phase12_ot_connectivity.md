# CascadeGuard AI — Real-Time Industrial OT Connectivity & Simulation Architecture (Phase 12)

This report documents the design, OT protocol adapters (Modbus TCP, OPC-UA, MQTT), normalized telemetry schema, mock simulation engine, telemetry manager, frontend control center, and security provisions introduced in Phase 12.

---

## 1. OT ADAPTER ARCHITECTURE OVERVIEW

Phase 12 introduces a production-style Industrial OT Connectivity Layer (`backend/ot/`) enabling CascadeGuard to interface with physical industrial PLCs, RTUs, BMS servers, and IoT brokers when connected, while offering a dynamic simulation mode for hackathon demonstrations:

```text
                               ┌────────────────────────────────────────┐
                               │       Telemetry Manager Interface      │
                               │  (Mode Switcher: MOCK vs REAL_OT)       │
                               └───────────────────┬────────────────────┘
                                                   │
             ┌─────────────────────────────────────┼─────────────────────────────────────┐
             │                                     │                                     │
             ▼                                     ▼                                     ▼
┌─────────────────────────┐           ┌─────────────────────────┐           ┌─────────────────────────┐
│   Modbus TCP Adapter    │           │     OPC-UA Adapter      │           │      MQTT Adapter       │
│  (Holding & Input Regs) │           │ (Kepware, S7, Ignition) │           │  (Industrial IoT Broker)│
└────────────┬────────────┘           └────────────┬────────────┘           └────────────┬────────────┘
             │                                     │                                     │
             └─────────────────────────────────────┼─────────────────────────────────────┘
                                                   │
                                                   ▼ (Fallback if disconnected)
                               ┌────────────────────────────────────────┐
                               │  Mock Industrial Telemetry Generator   │
                               │   (6 Plausible Dynamic Scenarios)      │
                               └───────────────────┬────────────────────┘
                                                   │
                                                   ▼
                               ┌────────────────────────────────────────┐
                               │     Unified Telemetry Schema & Quality │
                               │(Freshness, Validation, Mode Badges)    │
                               └───────────────────┬────────────────────┘
                                                   │
                                                   ▼
                               ┌────────────────────────────────────────┐
                               │ Downstream ML Inference & Cascade Graph│
                               └────────────────────────────────────────┘
```

---

## 2. SUPPORTED INDUSTRIAL OT PROTOCOLS

1. **Modbus TCP Adapter (`modbus_adapter.py`)**:
   - Configuration: `MODBUS_HOST`, `MODBUS_PORT` (default 502), `MODBUS_UNIT_ID` (1), `MODBUS_TIMEOUT` (3.0s).
   - Register Mappings:
     - **Transformer**: OTI (30001), WTI (30002), ATI (30003), OLI (30004), VL1..3, IL1..3.
     - **HVAC Chiller**: TEI (30010), TEO (30011), TCI (30012), TCO (30013), kW (30014).
     - **Water Pump**: flow (30020), pressure (30021), motor_temperature (30022), vibration (30023).
   - Fallback: Safely returns `connection_status = "DISCONNECTED"` if host unreachable.

2. **OPC-UA Adapter (`opcua_adapter.py`)**:
   - Configuration: `OPCUA_ENDPOINT`, `OPCUA_USERNAME`, `OPCUA_PASSWORD`.
   - Maps OPC-UA node IDs to asset fields. Safely falls back if server unavailable.

3. **MQTT Industrial IoT Adapter (`mqtt_adapter.py`)**:
   - Configuration: `MQTT_BROKER`, `MQTT_PORT` (1883), `MQTT_USERNAME`, `MQTT_PASSWORD`.
   - Topics: `cascadeguard/transformer/+/telemetry`, `cascadeguard/chiller/+/telemetry`, `cascadeguard/pump/+/telemetry`.

---

## 3. UNIFIED TELEMETRY SCHEMA

Every telemetry payload returned by `TelemetryManager` follows the standardized schema:

```json
{
  "asset_id": "TX-001",
  "asset_type": "TRANSFORMER",
  "timestamp": "2026-08-17 18:27:50",
  "source": "mock_telemetry",
  "mode": "MOCK",
  "freshness": "RECENT",
  "connection_status": "SIMULATED",
  "data_quality": {
    "complete": true,
    "missing_fields": [],
    "validation_errors": []
  },
  "telemetry": {
    "OTI": 51.04,
    "WTI": 56.97,
    "ATI": 31.2,
    "OLI": 85.0,
    "KW": 800.0,
    "VL1": 11.02
  }
}
```

---

## 4. MOCK SIMULATION SCENARIOS

The simulation engine (`mock_adapter.py`) supports 6 dynamic, physically plausible engineering scenarios:

1. `NORMAL`: Baseline operation across Transformer, Chiller, Water Pump.
2. `HIGH_LOAD`: Demand surge on Transformer ($+60\%$), Chiller power surge, Pump demand increase.
3. `HEAT_STRESS`: Ambient surge ($>42^\circ\text{C}$), Chiller condenser heat rejection stress.
4. `CHILLER_OVERLOAD`: Chiller evaporator/condenser thermal accumulation, power surge to $310\text{ kW}$.
5. `PUMP_DEGRADATION`: Water pump flow drops ($~62\text{ L/m}$), motor temperature & vibration surge.
6. `COMBINED_CASCADE`: Compound multi-asset failure propagating across Pump, Chiller, Transformer, and Climate Risk Engine.

---

## 5. NEW API ENDPOINTS

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/telemetry/status` | Adapter status, active mode (`MOCK`/`REAL_OT`), active scenario |
| `GET` | `/api/telemetry/live` | Normalized live telemetry across all assets |
| `POST` | `/api/telemetry/mode` | Switches mode between `MOCK` and `REAL_OT` |
| `POST` | `/api/telemetry/scenario` | Selects active simulation scenario |
| `GET` | `/api/telemetry/asset/<id>` | Telemetry schema for a specific asset |

---

## 6. SECURITY & SCIENTIFIC HONESTY PROVISIONS

- **Zero Hardcoded Credentials**: Passwords, IP addresses, and tokens are read strictly from `.env` environment variables.
- **Explicit Provenance Labels**: Simulation data is explicitly tagged as `MOCK` / `SIMULATED` / `ENGINEERING SCENARIO SIMULATION`.
- **Water Pump Limitation**: Water Pump model remains strictly designated as **`DECISION_SUPPORT_ONLY`**.

"""
CascadeGuard AI — Mock Industrial Telemetry Generator
Phase 12: Real-Time Industrial OT Connectivity + Telemetry Simulation

Generates dynamic, physically plausible telemetry streams for demonstration & simulation mode.
Explicitly labels all output with mode="MOCK", source="mock_telemetry", connection_status="SIMULATED".
"""

import time
import numpy as np

try:
    from ot.base_adapter import BaseTelemetryAdapter
except ImportError:
    from base_adapter import BaseTelemetryAdapter


class MockTelemetryAdapter(BaseTelemetryAdapter):
    def __init__(self, asset_id, asset_type):
        super().__init__(asset_id, asset_type, source_name="mock_telemetry")
        self.mode = "MOCK"
        self.connection_status = "SIMULATED"
        self.current_scenario = "NORMAL"
        self.step_counter = 0

    def connect(self):
        self.connection_status = "SIMULATED"
        return True

    def disconnect(self):
        self.connection_status = "SIMULATED"

    def health_check(self):
        return True

    def set_scenario(self, scenario_name):
        valid = ["NORMAL", "HIGH_LOAD", "HEAT_STRESS", "CHILLER_OVERLOAD", "PUMP_DEGRADATION", "COMBINED_CASCADE"]
        if scenario_name in valid:
            self.current_scenario = scenario_name
            self.step_counter = 0
            return True
        return False

    def read_telemetry(self):
        self.step_counter += 1
        t = self.step_counter
        noise = np.random.normal(0, 0.3)

        sc = self.current_scenario
        data = {}

        if self.asset_type == "TRANSFORMER":
            base_oti = 50.0 + 3.0 * np.sin(t / 5.0) + noise
            base_wti = base_oti + 6.0 + 0.5 * noise
            base_ati = 30.0 + 2.0 * np.sin(t / 10.0)
            base_oli = 85.0
            base_kw = 800.0 + 50.0 * np.sin(t / 4.0)

            if sc == "HIGH_LOAD":
                base_kw += 450.0
                base_oti += 18.0
                base_wti += 24.0
            elif sc == "HEAT_STRESS":
                base_ati = 43.5 + noise
                base_oti += 22.0
                base_wti += 26.0
            elif sc == "PUMP_DEGRADATION":
                # Reduced cooling flow causes gradual thermal accumulation
                base_oti += 12.0
                base_wti += 15.0
            elif sc == "CHILLER_OVERLOAD":
                base_oti += 10.0
            elif sc == "COMBINED_CASCADE":
                base_ati = 44.0
                base_kw += 500.0
                base_oti += 32.0
                base_wti += 38.0
                base_oli = 65.0

            data = {
                "OTI": round(float(np.clip(base_oti, 20.0, 110.0)), 2),
                "WTI": round(float(np.clip(base_wti, 25.0, 125.0)), 2),
                "ATI": round(float(np.clip(base_ati, 10.0, 55.0)), 2),
                "OLI": round(float(np.clip(base_oli, 0.0, 100.0)), 2),
                "VL1": round(float(11.0 + 0.05 * np.cos(t / 3.0)), 2),
                "VL2": round(float(11.0 + 0.04 * np.sin(t / 3.0)), 2),
                "VL3": round(float(11.01 + 0.03 * np.cos(t / 2.0)), 2),
                "IL1": round(float(base_kw / 2.0), 1),
                "IL2": round(float(base_kw / 2.01), 1),
                "IL3": round(float(base_kw / 1.99), 1),
                "KW": round(float(base_kw), 1),
                "H2": round(float(25.0 + (120.0 if sc == "COMBINED_CASCADE" else 0.0)), 1),
                "CH4": round(float(15.0 + (90.0 if sc == "COMBINED_CASCADE" else 0.0)), 1),
                "C2H2": round(float(0.5 + (18.0 if sc == "COMBINED_CASCADE" else 0.0)), 1)
            }

        elif self.asset_type == "CHILLER":
            tei = 12.0 + 0.5 * np.sin(t / 4.0) + noise
            teo = 7.0 + 0.3 * np.sin(t / 4.0)
            tci = 28.0 + 1.0 * np.sin(t / 8.0)
            tco = 33.0 + 1.2 * np.sin(t / 8.0)
            kw = 180.0 + 10.0 * np.cos(t / 5.0)

            if sc == "HEAT_STRESS":
                tci = 38.5 + noise
                tco = 44.0 + noise
                kw += 60.0
            elif sc == "HIGH_LOAD":
                kw += 90.0
                teo += 2.5
            elif sc == "PUMP_DEGRADATION":
                # Cooling water flow drop causes condenser temperature spike
                tci += 8.0
                tco += 11.0
                kw += 75.0
            elif sc == "CHILLER_OVERLOAD" or sc == "COMBINED_CASCADE":
                tei = 22.0
                teo = 16.5
                tci = 42.0
                tco = 49.0
                kw = 310.0

            data = {
                "TEI": round(float(tei), 2),
                "TEO": round(float(teo), 2),
                "TCI": round(float(tci), 2),
                "TCO": round(float(tco), 2),
                "kW": round(float(kw), 1),
                "chiller_id": self.asset_id
            }

        elif self.asset_type == "WATER_PUMP":
            flow = 125.0 + 3.0 * np.sin(t / 6.0) + noise
            press = 4.2 + 0.1 * np.cos(t / 4.0)
            motor_t = 48.0 + 1.0 * np.sin(t / 8.0)
            vib = 1.5 + 0.1 * noise

            if sc == "HIGH_LOAD":
                flow += 25.0
                motor_t += 6.0
            elif sc == "HEAT_STRESS":
                motor_t += 12.0
            elif sc == "PUMP_DEGRADATION" or sc == "COMBINED_CASCADE":
                flow = 62.0 + noise  # Severe 50% flow reduction
                press = 2.1 + 0.1 * noise
                motor_t = 78.5 + noise
                vib = 4.8 + 0.2 * noise  # Severe vibration spike

            data = {
                "flow": round(float(max(0.0, flow)), 2),
                "pressure": round(float(max(0.0, press)), 2),
                "motor_temperature": round(float(motor_t), 2),
                "vibration": round(float(max(0.0, vib)), 2),
                "pump_id": self.asset_id
            }

        quality = {
            "complete": True,
            "missing_fields": [],
            "validation_errors": [],
            "scenario": sc,
            "disclaimer": "ENGINEERING SCENARIO SIMULATION — DEMO MODE"
        }

        return self.format_telemetry_schema(data, quality)

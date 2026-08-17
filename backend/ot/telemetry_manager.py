"""
CascadeGuard AI — Industrial Telemetry Manager
Phase 12: Real-Time Industrial OT Connectivity + Telemetry Simulation

Manages real OT protocol adapters (Modbus TCP, OPC-UA, MQTT) and simulation mock adapters.
Performs data validation, quality checking, freshness calculation, and safe mode switching.
"""

import os
import time

try:
    from ot.mock_adapter import MockTelemetryAdapter
    from ot.modbus_adapter import ModbusTCPAdapter
    from ot.opcua_adapter import OPCUAAdapter
    from ot.mqtt_adapter import MQTTAdapter
except ImportError:
    from mock_adapter import MockTelemetryAdapter
    from modbus_adapter import ModbusTCPAdapter
    from opcua_adapter import OPCUAAdapter
    from mqtt_adapter import MQTTAdapter


class TelemetryManager:
    def __init__(self):
        env_mode = os.environ.get("TELEMETRY_MODE", "MOCK").upper()
        self.mode = "REAL_OT" if env_mode == "REAL_OT" else "MOCK"
        self.active_scenario = "NORMAL"

        # Active asset adapters
        self.adapters = {
            "transformer": {
                "mock": MockTelemetryAdapter("TX-001", "TRANSFORMER"),
                "modbus": ModbusTCPAdapter("TX-001", "TRANSFORMER"),
                "opcua": OPCUAAdapter("TX-001", "TRANSFORMER"),
                "mqtt": MQTTAdapter("TX-001", "TRANSFORMER")
            },
            "chiller": {
                "mock": MockTelemetryAdapter("CH-001", "CHILLER"),
                "modbus": ModbusTCPAdapter("CH-001", "CHILLER"),
                "opcua": OPCUAAdapter("CH-001", "CHILLER"),
                "mqtt": MQTTAdapter("CH-001", "CHILLER")
            },
            "water_pump": {
                "mock": MockTelemetryAdapter("WP-001", "WATER_PUMP"),
                "modbus": ModbusTCPAdapter("WP-001", "WATER_PUMP"),
                "opcua": OPCUAAdapter("WP-001", "WATER_PUMP"),
                "mqtt": MQTTAdapter("WP-001", "WATER_PUMP")
            }
        }

        # Initialize mock adapters
        for key in self.adapters:
            self.adapters[key]["mock"].connect()

    def set_mode(self, mode_str):
        upper_mode = str(mode_str).upper().strip()
        if upper_mode in ["MOCK", "REAL_OT"]:
            self.mode = upper_mode
            return True
        return False

    def set_scenario(self, scenario_name):
        valid = ["NORMAL", "HIGH_LOAD", "HEAT_STRESS", "CHILLER_OVERLOAD", "PUMP_DEGRADATION", "COMBINED_CASCADE"]
        if scenario_name in valid:
            self.active_scenario = scenario_name
            for key in self.adapters:
                self.adapters[key]["mock"].set_scenario(scenario_name)
            return True
        return False

    def validate_telemetry(self, asset_type, telemetry_dict):
        missing = []
        errors = []

        if not isinstance(telemetry_dict, dict) or len(telemetry_dict) == 0:
            return False, ["telemetry_empty"], ["Telemetry data dictionary is empty"]

        if asset_type == "TRANSFORMER":
            oti = telemetry_dict.get("OTI")
            wti = telemetry_dict.get("WTI")
            if oti is not None and (oti < -40.0 or oti > 150.0):
                errors.append(f"Invalid OTI temperature ({oti}°C). Out of physical bounds [-40, 150].")
            if wti is not None and (wti < -40.0 or wti > 160.0):
                errors.append(f"Invalid WTI temperature ({wti}°C). Out of physical bounds [-40, 160].")

        elif asset_type == "CHILLER":
            tei = telemetry_dict.get("TEI")
            kw = telemetry_dict.get("kW")
            if tei is not None and (tei < -30.0 or tei > 80.0):
                errors.append(f"Invalid evaporator temperature TEI ({tei}°C).")
            if kw is not None and kw < 0.0:
                errors.append(f"Invalid negative power consumption ({kw} kW).")

        elif asset_type == "WATER_PUMP":
            flow = telemetry_dict.get("flow")
            press = telemetry_dict.get("pressure")
            vib = telemetry_dict.get("vibration")

            if flow is not None and flow < 0.0:
                errors.append(f"Invalid negative water flow ({flow} L/min).")
            if press is not None and press < 0.0:
                errors.append(f"Invalid negative water pressure ({press} bar).")
            if vib is not None and vib < 0.0:
                errors.append(f"Invalid negative vibration ({vib} mm/s).")

        is_complete = len(missing) == 0 and len(errors) == 0
        return is_complete, missing, errors

    def get_asset_telemetry(self, asset_category, asset_id="TX-001"):
        category = asset_category.lower()
        if category not in self.adapters:
            category = "transformer"

        adapter_group = self.adapters[category]

        # In REAL_OT mode, attempt Modbus / OPCUA / MQTT first
        if self.mode == "REAL_OT":
            for protocol in ["modbus", "opcua", "mqtt"]:
                adapter = adapter_group[protocol]
                if adapter.connection_status == "DISCONNECTED":
                    adapter.connect()

                if adapter.connection_status == "CONNECTED":
                    rec = adapter.read_telemetry()
                    is_valid, miss, errs = self.validate_telemetry(adapter.asset_type, rec.get("telemetry", {}))
                    rec["data_quality"]["complete"] = is_valid
                    rec["data_quality"]["missing_fields"].extend(miss)
                    rec["data_quality"]["validation_errors"].extend(errs)
                    return rec

            # If all REAL_OT adapters are unreachable, return DISCONNECTED payload with fallback explanation
            mock_rec = adapter_group["mock"].read_telemetry()
            mock_rec["mode"] = "REAL_OT (FALLBACK_TO_MOCK)"
            mock_rec["connection_status"] = "UNREACHABLE_FALLBACK"
            mock_rec["data_quality"]["validation_errors"].append("REAL_OT endpoints unreachable; falling back to simulation adapter.")
            return mock_rec

        # MOCK MODE
        mock_rec = adapter_group["mock"].read_telemetry()
        is_valid, miss, errs = self.validate_telemetry(mock_rec["asset_type"], mock_rec.get("telemetry", {}))
        mock_rec["data_quality"]["complete"] = is_valid
        mock_rec["data_quality"]["missing_fields"].extend(miss)
        mock_rec["data_quality"]["validation_errors"].extend(errs)
        return mock_rec

    def get_all_live_telemetry(self):
        return {
            "transformer": self.get_asset_telemetry("transformer"),
            "chiller": self.get_asset_telemetry("chiller"),
            "water_pump": self.get_asset_telemetry("water_pump")
        }

    def get_status(self):
        status_dict = {}
        for key in self.adapters:
            active_adapter = self.adapters[key]["mock"] if self.mode == "MOCK" else self.adapters[key]["modbus"]
            status_dict[key] = {
                "asset_id": active_adapter.asset_id,
                "mode": self.mode,
                "active_scenario": self.active_scenario,
                "source": active_adapter.source_name if self.mode == "REAL_OT" else "mock_telemetry",
                "connection_status": active_adapter.connection_status if self.mode == "REAL_OT" else "SIMULATED",
                "is_healthy": active_adapter.health_check()
            }
        return status_dict

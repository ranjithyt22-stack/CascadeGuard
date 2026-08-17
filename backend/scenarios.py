import copy
# pyrefly: ignore [missing-import]
import numpy as np

SCENARIOS_METADATA = {
    "NORMAL": {
        "name": "NORMAL",
        "label": "Normal Operation",
        "description": "Baseline multi-asset telemetry with standard operating conditions across all infrastructure.",
        "icon": "🟢",
        "category": "Baseline"
    },
    "THERMAL_OVERLOAD": {
        "name": "THERMAL_OVERLOAD",
        "label": "Thermal Overload",
        "description": "Elevated winding and oil temperature index indicating severe transformer thermal stress.",
        "icon": "🔥",
        "category": "Operational"
    },
    "HIGH_POWER_DEMAND": {
        "name": "HIGH_POWER_DEMAND",
        "label": "High Power Demand",
        "description": "Surge in active power demand and maximum power demand on substation transformer.",
        "icon": "⚡",
        "category": "Operational"
    },
    "HIGH_CHILLER_RISK": {
        "name": "HIGH_CHILLER_RISK",
        "label": "High Chiller Risk (Fault Mode 4/7)",
        "description": "Simulated condenser water flow restriction and compressor valve drag on HVAC Chiller.",
        "icon": "❄️",
        "category": "Multi-Asset Scenario"
    },
    "PUMP_COOLING_SCENARIO": {
        "name": "PUMP_COOLING_SCENARIO",
        "label": "Pump Cooling Degradation",
        "description": "Simulated cooling water flow drop and pump mechanical degradation.",
        "icon": "💧",
        "category": "Multi-Asset Scenario"
    },
    "EXTREME_HEAT": {
        "name": "EXTREME_HEAT",
        "label": "Extreme Heatwave",
        "description": "Simulated heatwave with ambient temperature exceeding 46°C.",
        "icon": "☀️",
        "category": "Environmental"
    },
    "COMBINED_CASCADE": {
        "name": "COMBINED_CASCADE",
        "label": "Combined Cascade Scenario",
        "description": "Compound stress combining heatwave, pump flow drop, chiller fault, and transformer thermal overload.",
        "icon": "💥",
        "category": "Compound Critical"
    }
}


def get_available_scenarios():
    return list(SCENARIOS_METADATA.values())


def apply_scenario(scenario_name, op_data_raw, op_data_v3, health_data, climate_data, chiller_data=None, pump_data=None):
    name = str(scenario_name).upper().strip()
    if name not in SCENARIOS_METADATA:
        name = "NORMAL"

    mod_op_raw = copy.deepcopy(op_data_raw)
    mod_op_v3 = copy.deepcopy(op_data_v3)
    mod_health = copy.deepcopy(health_data)
    mod_climate = copy.deepcopy(climate_data)
    mod_chiller = copy.deepcopy(chiller_data) if chiller_data is not None else {}
    mod_pump = copy.deepcopy(pump_data) if pump_data is not None else {}

    deltas = []

    def record_change(feat, orig_val, new_val):
        o = float(orig_val) if orig_val is not None and not np.isnan(orig_val) else 0.0
        n = float(new_val) if new_val is not None and not np.isnan(new_val) else 0.0
        deltas.append({
            "feature": feat,
            "baseline": round(o, 2),
            "scenario": round(n, 2),
            "change": round(n - o, 2)
        })

    if name == "NORMAL":
        pass

    elif name == "THERMAL_OVERLOAD":
        orig_oti = float(mod_op_raw.get("OTI", 29.0))
        mod_op_raw["OTI"] = orig_oti + 28.0
        record_change("OTI", orig_oti, mod_op_raw["OTI"])

        orig_wti = float(mod_op_raw.get("WTI", 32.0))
        mod_op_raw["WTI"] = orig_wti + 32.0
        record_change("WTI", orig_wti, mod_op_raw["WTI"])

        orig_kw = float(mod_op_raw.get("KW", 100.0))
        mod_op_raw["KW"] = max(orig_kw * 2.2, 220.0)
        record_change("KW", orig_kw, mod_op_raw["KW"])

        for feat_name in ["OTI", "WTI", "KW"]:
            val = mod_op_raw[feat_name]
            mod_op_v3[feat_name] = val
            mod_op_v3[f"{feat_name}_roll30m_mean"] = val
            mod_op_v3[f"{feat_name}_roll60m_mean"] = val
            mod_op_v3[f"{feat_name}_roll60m_max"] = val

    elif name == "HIGH_POWER_DEMAND":
        orig_kw = float(mod_op_raw.get("KW", 100.0))
        mod_op_raw["KW"] = max(orig_kw * 2.5, 250.0)
        record_change("KW", orig_kw, mod_op_raw["KW"])

        for feat_name in ["KW"]:
            val = mod_op_raw[feat_name]
            mod_op_v3[feat_name] = val
            mod_op_v3[f"{feat_name}_roll30m_mean"] = val
            mod_op_v3[f"{feat_name}_roll60m_mean"] = val

    elif name == "HIGH_CHILLER_RISK":
        if mod_chiller:
            mod_chiller["TCI"] = float(mod_chiller.get("TCI", 30.0)) + 12.0
            mod_chiller["TCO"] = float(mod_chiller.get("TCO", 35.0)) + 14.0
            mod_chiller["kW"] = float(mod_chiller.get("kW", 100.0)) * 1.8
            mod_chiller["TRC_sub"] = float(mod_chiller.get("TRC_sub", 5.0)) + 8.0
            record_change("Chiller TCI", 30.0, mod_chiller["TCI"])

    elif name == "PUMP_COOLING_SCENARIO":
        if mod_pump:
            mod_pump["sensor_00"] = max(float(mod_pump.get("sensor_00", 2.4)) - 1.8, 0.2)
            mod_pump["sensor_13"] = float(mod_pump.get("sensor_13", 10.0)) + 15.0
            record_change("Pump Sensor_00", 2.4, mod_pump["sensor_00"])

    elif name == "EXTREME_HEAT":
        orig_ati = float(mod_op_raw.get("ATI", 30.0))
        mod_op_raw["ATI"] = max(orig_ati + 16.0, 46.0)
        record_change("ATI", orig_ati, mod_op_raw["ATI"])

        orig_temp = float(mod_climate.get("temperature", 28.0))
        mod_climate["temperature"] = max(orig_temp + 16.0, 46.0)
        record_change("climate_temperature", orig_temp, mod_climate["temperature"])

        heat = min(max((mod_climate["temperature"] - 30) / 15 * 100, 0), 100)
        hum = min(max((float(mod_climate.get("humidity", 60)) - 60) / 40 * 100, 0), 100)
        rn = min(max(float(mod_climate.get("rain", 0)) / 20 * 100, 0), 100)
        wnd = min(max((float(mod_climate.get("wind", 10)) - 30) / 40 * 100, 0), 100)
        mod_climate["climate_stress"] = round(heat * 0.45 + hum * 0.20 + rn * 0.20 + wnd * 0.15, 2)

    elif name == "COMBINED_CASCADE":
        orig_oti = float(mod_op_raw.get("OTI", 29.0))
        mod_op_raw["OTI"] = orig_oti + 30.0
        record_change("OTI", orig_oti, mod_op_raw["OTI"])

        if mod_chiller:
            mod_chiller["TCI"] = float(mod_chiller.get("TCI", 30.0)) + 14.0
            mod_chiller["kW"] = float(mod_chiller.get("kW", 100.0)) * 2.0

        if mod_pump:
            mod_pump["sensor_00"] = 0.3

        orig_temp = float(mod_climate.get("temperature", 28.0))
        mod_climate["temperature"] = max(orig_temp + 16.0, 46.0)
        record_change("climate_temperature", orig_temp, mod_climate["temperature"])

        heat = min(max((mod_climate["temperature"] - 30) / 15 * 100, 0), 100)
        hum = min(max((float(mod_climate.get("humidity", 60)) - 60) / 40 * 100, 0), 100)
        rn = min(max(float(mod_climate.get("rain", 0)) / 20 * 100, 0), 100)
        wnd = min(max((float(mod_climate.get("wind", 10)) - 30) / 40 * 100, 0), 100)
        mod_climate["climate_stress"] = round(heat * 0.45 + hum * 0.20 + rn * 0.20 + wnd * 0.15, 2)

    meta = SCENARIOS_METADATA.get(name, SCENARIOS_METADATA["NORMAL"])

    # Store modified chiller and pump inside climate dict or return 6 elements for backward compatibility
    mod_climate["_mod_chiller"] = mod_chiller
    mod_climate["_mod_pump"] = mod_pump

    return mod_op_raw, mod_op_v3, mod_health, mod_climate, deltas, meta

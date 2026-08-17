"""
CascadeGuard AI — Climate Stress What-If Simulation Engine
Phase 11: Climate Stress What-If Simulation & Multi-Asset Cascade

Transforms live weather baseline measurements into simulated what-if climate scenarios
and models non-causal engineering scenario stress propagation across Chiller, Pump, and Transformer assets.

IMPORTANT SCIENTIFIC NOTICE:
- All scenario transformations are WHAT-IF SIMULATIONS for engineering decision support.
- They represent hypothetical scenario conditions, NOT real observed physical sensor readings.
"""

import copy
import numpy as np

CLIMATE_SCENARIO_DEFINITIONS = {
    "NORMAL": {
        "name": "NORMAL",
        "label": "Current Conditions (Live API)",
        "description": "Unmodified live weather baseline retrieved directly from Open-Meteo API.",
        "icon": "🟢",
        "is_simulated": False
    },
    "HEATWAVE": {
        "name": "HEATWAVE",
        "label": "Heatwave Surge",
        "description": "Simulated heatwave with temperature increased by +6.5°C above current baseline.",
        "icon": "☀️",
        "is_simulated": True
    },
    "EXTREME_HEAT": {
        "name": "EXTREME_HEAT",
        "label": "Extreme Heatwave",
        "description": "Severe ambient heatwave surging temperature above 46.0°C with solar thermal stress.",
        "icon": "🔥",
        "is_simulated": True
    },
    "HIGH_HUMIDITY": {
        "name": "HIGH_HUMIDITY",
        "label": "High Humidity / Tropical Damp",
        "description": "Simulated humidity surge to 95% with elevated dew point and air density stress.",
        "icon": "🌫️",
        "is_simulated": True
    },
    "HEAVY_RAIN": {
        "name": "HEAVY_RAIN",
        "label": "Heavy Monsoon Precipitation",
        "description": "Simulated tropical downpour with 25 mm/h precipitation.",
        "icon": "🌧️",
        "is_simulated": True
    },
    "COOLING_FAILURE": {
        "name": "COOLING_FAILURE",
        "label": "Chiller Cooling Restriction",
        "description": "HVAC Chiller condenser flow restriction and valve drag simulation.",
        "icon": "❄️",
        "is_simulated": True
    },
    "PUMP_DEGRADATION": {
        "name": "PUMP_DEGRADATION",
        "label": "Cooling Water Pump Flow Drop",
        "description": "Cooling water pump mechanical flow drop and impeller vibration surge.",
        "icon": "💧",
        "is_simulated": True
    },
    "COMBINED_CASCADE": {
        "name": "COMBINED_CASCADE",
        "label": "Combined Extreme Cascade",
        "description": "Compound extreme stress combining heatwave (+8°C), pump flow drop, chiller fault, and thermal overload.",
        "icon": "💥",
        "is_simulated": True
    }
}


def get_supported_climate_scenarios():
    return list(CLIMATE_SCENARIO_DEFINITIONS.values())


def compute_climate_stress(temp, hum, rain, wind):
    t = float(temp) if temp is not None else 28.5
    h = float(hum) if hum is not None else 60.0
    r = float(rain) if rain is not None else 0.0
    w = float(wind) if wind is not None else 10.0

    heat_stress = np.clip((t - 30.0) / 15.0 * 100.0, 0.0, 100.0)
    hum_stress = np.clip((h - 60.0) / 40.0 * 100.0, 0.0, 100.0)
    rain_stress = np.clip(r / 20.0 * 100.0, 0.0, 100.0)
    wind_stress = np.clip((w - 30.0) / 40.0 * 100.0, 0.0, 100.0)

    stress = heat_stress * 0.45 + hum_stress * 0.20 + rain_stress * 0.20 + wind_stress * 0.15
    return round(float(stress), 2)


def apply_climate_scenario_transform(baseline_climate, scenario_name):
    name = str(scenario_name).upper().strip()
    if name not in CLIMATE_SCENARIO_DEFINITIONS:
        name = "NORMAL"

    b_temp = float(baseline_climate.get("temperature", 28.5))
    b_hum = float(baseline_climate.get("humidity", 65.0))
    b_rain = float(baseline_climate.get("rain", 0.0))
    b_wind = float(baseline_climate.get("wind", 12.0))
    b_stress = float(baseline_climate.get("climate_stress", compute_climate_stress(b_temp, b_hum, b_rain, b_wind)))

    s_temp, s_hum, s_rain, s_wind = b_temp, b_hum, b_rain, b_wind

    if name == "NORMAL":
        pass
    elif name == "HEATWAVE":
        s_temp = max(b_temp + 6.5, 38.0)
    elif name == "EXTREME_HEAT":
        s_temp = max(b_temp + 14.0, 46.5)
    elif name == "HIGH_HUMIDITY":
        s_hum = 95.0
    elif name == "HEAVY_RAIN":
        s_rain = 25.0
        s_wind = max(b_wind + 15.0, 35.0)
    elif name == "COOLING_FAILURE":
        s_temp = max(b_temp + 3.0, 33.0)
    elif name == "PUMP_DEGRADATION":
        s_temp = max(b_temp + 2.0, 32.0)
    elif name == "COMBINED_CASCADE":
        s_temp = max(b_temp + 12.0, 45.0)
        s_hum = 90.0
        s_rain = 20.0
        s_wind = max(b_wind + 10.0, 30.0)

    s_stress = compute_climate_stress(s_temp, s_hum, s_rain, s_wind)
    if name in ["COOLING_FAILURE", "PUMP_DEGRADATION", "COMBINED_CASCADE"]:
        s_stress = min(s_stress + 15.0, 100.0)

    stress_change = round(s_stress - b_stress, 2)
    meta = CLIMATE_SCENARIO_DEFINITIONS[name]

    return {
        "scenario_name": name,
        "label": meta["label"],
        "description": meta["description"],
        "icon": meta["icon"],
        "is_simulated": meta["is_simulated"],
        "baseline": {
            "temperature": round(b_temp, 1),
            "humidity": round(b_hum, 1),
            "rain": round(b_rain, 1),
            "wind": round(b_wind, 1),
            "climate_stress": round(b_stress, 2)
        },
        "scenario": {
            "temperature": round(s_temp, 1),
            "humidity": round(s_hum, 1),
            "rain": round(s_rain, 1),
            "wind": round(s_wind, 1),
            "climate_stress": round(s_stress, 2)
        },
        "stress_change": stress_change
    }

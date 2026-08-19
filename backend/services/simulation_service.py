"""
backend/services/simulation_service.py
======================================
CascadeGuard AI — Climate & Infrastructure Simulation Engine (Phase G)

Runs what-if climate scenarios (HEATWAVE, HEAVY RAIN, HIGH LOAD, COOLING FAILURE, COMBINED EXTREME)
and evaluates complete causal propagation through ML models and Recommendation Engine.
"""
from services.cascade_service import evaluate_cascade_risk
from services.recommendation_service import generate_recommendations

SCENARIOS_PRESETS = {
    "BASELINE": {
        "name": "Baseline Operating Envelope",
        "description": "Nominal weather and facility electrical demand.",
        "temperature_c": 30.0,
        "relative_humidity": 55.0,
        "rainfall_mm": 0.0,
        "hospital_load_kw": 850.0,
        "cooling_efficiency_cop": 4.0
    },
    "HEATWAVE": {
        "name": "Extreme Heatwave Event",
        "description": "Ambient temperature reaches 42°C with high humidity, driving peak HVAC cooling demand.",
        "temperature_c": 42.0,
        "relative_humidity": 75.0,
        "rainfall_mm": 0.0,
        "hospital_load_kw": 1450.0,
        "cooling_efficiency_cop": 3.2
    },
    "HEAVY RAIN": {
        "name": "Monsoon Torrential Rain",
        "description": "Heavy rainfall of 65mm/h causing surface water accumulation and flood risk.",
        "temperature_c": 26.0,
        "relative_humidity": 95.0,
        "rainfall_mm": 65.0,
        "hospital_load_kw": 920.0,
        "cooling_efficiency_cop": 3.8
    },
    "HIGH LOAD": {
        "name": "Peak Medical Surge Demand",
        "description": "ICU and OT emergency surge increasing electrical demand to 1600 kW.",
        "temperature_c": 34.0,
        "relative_humidity": 60.0,
        "rainfall_mm": 0.0,
        "hospital_load_kw": 1600.0,
        "cooling_efficiency_cop": 3.5
    },
    "COOLING FAILURE": {
        "name": "Chiller Compressor Trip",
        "description": "HVAC Chiller C1 experiences partial refrigerant leak, reducing COP efficiency to 1.8.",
        "temperature_c": 36.0,
        "relative_humidity": 65.0,
        "rainfall_mm": 0.0,
        "hospital_load_kw": 1250.0,
        "cooling_efficiency_cop": 1.8
    },
    "COMBINED EXTREME": {
        "name": "Combined Heatwave + Surge + Chiller Fault",
        "description": "Simultaneous 42°C heatwave, 1650 kW load surge, and chiller efficiency loss.",
        "temperature_c": 42.0,
        "relative_humidity": 80.0,
        "rainfall_mm": 25.0,
        "hospital_load_kw": 1650.0,
        "cooling_efficiency_cop": 1.6
    }
}

def run_simulation_scenario(
    scenario_key: str = "BASELINE",
    custom_params: dict = None
) -> dict:
    preset = SCENARIOS_PRESETS.get(scenario_key.upper(), SCENARIOS_PRESETS["BASELINE"]).copy()
    
    if custom_params:
        for k, v in custom_params.items():
            if v is not None and k in preset:
                preset[k] = float(v)
                
    # Format weather input for cascade risk engine
    weather_sim = {
        "current": {
            "temperature_2m": preset["temperature_c"],
            "relative_humidity_2m": preset["relative_humidity"],
            "precipitation": preset["rainfall_mm"],
            "surface_pressure": 1005.0 if preset["rainfall_mm"] > 30 else 1012.0
        }
    }
    
    # Run Cascade Risk Engine
    cascade_res = evaluate_cascade_risk(weather_sim)
    
    # Adjust for custom simulated parameters
    if preset["cooling_efficiency_cop"] < 2.5:
        cascade_res["overall_risk"] = min(0.95, cascade_res["overall_risk"] + 0.25)
        cascade_res["level"] = "CRITICAL"
        if "C1" not in cascade_res["affected_equipment"]:
            cascade_res["affected_equipment"].append("C1")
        cascade_res["drivers"].append("reduced chiller COP efficiency")
        cascade_res["potential_downstream_impact"].append("critical cooling degradation in surgical operating theaters")
        
    # Generate Recommendations
    rec_res = generate_recommendations(cascade_res)
    
    return {
        "data_type": "SIMULATION",
        "simulation_label": "SIMULATION TELEMETRY",
        "scenario_key": scenario_key.upper(),
        "scenario_name": preset["name"],
        "scenario_description": preset["description"],
        "parameters": preset,
        "cascade_analysis": cascade_res,
        "recommendations": rec_res
    }

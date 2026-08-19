"""
backend/api/routes_scenarios_phase21.py
========================================
Phase 21 — Interactive Digital Twin & Manual What-If Climate Simulator Endpoints

Provides REST API endpoints for digital twin simulation, scenario presets, custom scenario saving,
scenario comparison, and intervention strategy optimization.
"""

from fastapi import APIRouter, Path, Query, HTTPException, Body
from fastapi.responses import JSONResponse
import time
from typing import Dict, Any, List, Optional

import state
from services.digital_twin_engine import digital_twin_engine


router = APIRouter()

# In-memory saved user scenarios storage
_SAVED_SCENARIOS: Dict[str, Dict[str, Any]] = {}


@router.get("/scenarios/presets")
def get_scenario_presets_endpoint():
    """Returns centralized preset configurations for the What-If Climate Simulator."""
    presets = [
        {
            "id": "CURRENT",
            "name": "Current Conditions",
            "icon": "CURRENT",
            "description": "Live Open-Meteo baseline weather and current operational configuration.",
            "inputs": {"temperature": 32.0, "humidity": 65.0, "rainfall": 0.0, "rain_probability": 20.0, "wind_speed": 12.0, "duration_hours": 6.0, "transformer_load": 80.0, "transformer_cooling": 100.0, "chiller_capacity": 100.0, "pump_flow": 100.0}
        },
        {
            "id": "HEATWAVE",
            "name": "Heatwave Stress",
            "icon": "HEATWAVE",
            "description": "Sustained ambient heatwave stress (+6.5°C above baseline) increasing cooling demand.",
            "inputs": {"temperature": 38.5, "humidity": 75.0, "rainfall": 0.0, "rain_probability": 10.0, "wind_speed": 8.0, "duration_hours": 6.0, "transformer_load": 88.0, "transformer_cooling": 100.0, "chiller_capacity": 100.0, "pump_flow": 100.0}
        },
        {
            "id": "EXTREME_HEAT",
            "name": "Extreme Heat Surge",
            "icon": "EXTREME_HEAT",
            "description": "Extreme 46.0°C temperature surge for 12 hours triggering transformer thermal overload.",
            "inputs": {"temperature": 46.0, "humidity": 80.0, "rainfall": 0.0, "rain_probability": 5.0, "wind_speed": 5.0, "duration_hours": 12.0, "transformer_load": 95.0, "transformer_cooling": 85.0, "chiller_capacity": 90.0, "pump_flow": 100.0}
        },
        {
            "id": "HIGH_HUMIDITY",
            "name": "High Humidity Stress",
            "icon": "HIGH_HUMIDITY",
            "description": "High relative humidity (95%) degrading HVAC chiller heat rejection efficiency.",
            "inputs": {"temperature": 36.0, "humidity": 95.0, "rainfall": 5.0, "rain_probability": 40.0, "wind_speed": 10.0, "duration_hours": 8.0, "transformer_load": 85.0, "transformer_cooling": 90.0, "chiller_capacity": 80.0, "pump_flow": 100.0}
        },
        {
            "id": "HEAVY_MONSOON",
            "name": "Heavy Monsoon Downpour",
            "icon": "HEAVY_MONSOON",
            "description": "Heavy monsoon precipitation (120mm over 12 hrs) testing industrial water pump capacity.",
            "inputs": {"temperature": 27.0, "humidity": 98.0, "rainfall": 120.0, "rain_probability": 95.0, "wind_speed": 35.0, "duration_hours": 12.0, "transformer_load": 70.0, "transformer_cooling": 100.0, "chiller_capacity": 100.0, "pump_flow": 80.0}
        },
        {
            "id": "CHILLER_RESTRICTION",
            "name": "Chiller Restriction",
            "icon": "CHILLER_RESTRICTION",
            "description": "HVAC Chiller cooling capacity restricted to 60% due to compressor fault.",
            "inputs": {"temperature": 37.0, "humidity": 70.0, "rainfall": 0.0, "rain_probability": 10.0, "wind_speed": 15.0, "duration_hours": 6.0, "transformer_load": 90.0, "transformer_cooling": 100.0, "chiller_capacity": 60.0, "pump_flow": 100.0, "toggle_chiller_restriction": True}
        },
        {
            "id": "PUMP_FLOW_DROP",
            "name": "Pump Flow Drop",
            "icon": "PUMP_FLOW_DROP",
            "description": "Industrial Water Pump flow drops to 50% flow capacity under rainfall inflow.",
            "inputs": {"temperature": 30.0, "humidity": 85.0, "rainfall": 40.0, "rain_probability": 80.0, "wind_speed": 20.0, "duration_hours": 8.0, "transformer_load": 75.0, "transformer_cooling": 100.0, "chiller_capacity": 100.0, "pump_flow": 50.0, "toggle_pump_failure": True}
        },
        {
            "id": "COMBINED_CASCADE",
            "name": "Combined System Cascade",
            "icon": "COMBINED_CASCADE",
            "description": "Multi-vector failure: Extreme heat + High humidity + Chiller restriction + 95% Transformer load.",
            "inputs": {"temperature": 44.0, "humidity": 90.0, "rainfall": 25.0, "rain_probability": 70.0, "wind_speed": 10.0, "duration_hours": 10.0, "transformer_load": 95.0, "transformer_cooling": 75.0, "chiller_capacity": 60.0, "pump_flow": 85.0, "toggle_cooling_failure": True, "toggle_chiller_restriction": True}
        }
    ]

    return {"success": True, "presets": presets, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}


@router.post("/scenarios/simulate")
def simulate_scenario_endpoint(payload: Dict[str, Any] = Body(...)):
    """Executes physics-based digital twin simulation for manual scenario inputs."""
    site_id = payload.get("site_id", "SITE-001")
    inputs = payload.get("inputs", {})
    if not inputs and "temperature" in payload:
        inputs = payload

    res = digital_twin_engine.simulate_digital_twin(site_id, inputs)
    return res


@router.post("/scenarios/save")
def save_scenario_endpoint(payload: Dict[str, Any] = Body(...)):
    """Saves a custom user scenario configuration."""
    site_id = payload.get("site_id", "SITE-001")
    scenario_name = payload.get("scenario_name", "Custom Scenario")
    inputs = payload.get("inputs", {})

    sc_id = f"SCEN-{int(time.time()*1000)}"
    sim_res = digital_twin_engine.simulate_digital_twin(site_id, inputs)

    record = {
        "scenario_id": sc_id,
        "site_id": site_id,
        "scenario_name": scenario_name,
        "inputs": inputs,
        "results": sim_res,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    _SAVED_SCENARIOS[sc_id] = record
    return {"success": True, "scenario_id": sc_id, "scenario": record}


@router.get("/scenarios/list")
def list_saved_scenarios_endpoint():
    """Lists saved custom user scenarios."""
    sc_list = list(_SAVED_SCENARIOS.values())
    sc_list.sort(key=lambda x: x["created_at"], reverse=True)
    return {"success": True, "count": len(sc_list), "scenarios": sc_list}


@router.post("/scenarios/compare")
def compare_scenarios_endpoint(payload: Dict[str, Any] = Body(...)):
    """Compares two scenario simulation outputs side-by-side."""
    site_id = payload.get("site_id", "SITE-001")
    inputs_a = payload.get("inputs_a", {})
    inputs_b = payload.get("inputs_b", {})

    sim_a = digital_twin_engine.simulate_digital_twin(site_id, inputs_a)
    sim_b = digital_twin_engine.simulate_digital_twin(site_id, inputs_b)

    risk_diff = round(sim_b["scenario"]["system_risk"] - sim_a["scenario"]["system_risk"], 2)
    resilience_diff = round(sim_b["scenario"]["resilience_score"] - sim_a["scenario"]["resilience_score"], 1)

    return {
        "success": True,
        "site_id": site_id,
        "scenario_a": sim_a,
        "scenario_b": sim_b,
        "comparison": {
            "system_risk_diff": risk_diff,
            "resilience_score_diff": resilience_diff,
            "interpretation": f"Scenario B system risk is {abs(risk_diff)} points {'higher' if risk_diff > 0 else 'lower'} than Scenario A."
        }
    }


@router.post("/scenarios/intervention")
def simulate_intervention_endpoint(payload: Dict[str, Any] = Body(...)):
    """Simulates intervention strategies against a specific scenario configuration."""
    site_id = payload.get("site_id", "SITE-001")
    inputs = payload.get("inputs", {})

    sim_res = digital_twin_engine.simulate_digital_twin(site_id, inputs)
    return {
        "success": True,
        "site_id": site_id,
        "base_scenario_risk": sim_res["scenario"]["system_risk"],
        "interventions": sim_res["interventions"]
    }

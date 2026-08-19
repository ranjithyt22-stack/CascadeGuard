"""
backend/api/routes_cascadeguard.py
==================================
CascadeGuard AI — Unified Core API Endpoints (Phase I)
- GET /api/predictions/load
- GET /api/predictions/transformer
- GET /api/predictions/chiller
- GET /api/predictions/pump
- GET /api/predictions/flood
- GET /api/cascade/current
- GET /api/recommendations
- GET /api/model-health
- POST /api/simulation/run
"""
import os
import requests
from fastapi import APIRouter, Query, Body
from fastapi.responses import JSONResponse

from services.cascade_service import evaluate_cascade_risk
from services.recommendation_service import generate_recommendations
from services.simulation_service import run_simulation_scenario, SCENARIOS_PRESETS
from services.model_health_service import get_model_health_report

router = APIRouter()

OPEN_METEO_BASE_URL = os.environ.get("OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1/forecast")
KMCH_LAT = float(os.environ.get("LATITUDE", 11.0168))
KMCH_LON = float(os.environ.get("LONGITUDE", 76.9558))

def _get_live_weather():
    try:
        r = requests.get(OPEN_METEO_BASE_URL, params={
            "latitude": KMCH_LAT, "longitude": KMCH_LON,
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,surface_pressure",
            "forecast_days": 1, "timezone": "Asia/Kolkata"
        }, timeout=5)
        return r.json()
    except Exception:
        return {"current": {"temperature_2m": 32.0, "relative_humidity_2m": 65.0, "precipitation": 0.0, "surface_pressure": 1008.0}}

@router.get("/predictions/load")
def get_prediction_load():
    weather = _get_live_weather()
    cascade = evaluate_cascade_risk(weather)
    return cascade["predictions"]["load"]

@router.get("/predictions/transformer")
def get_prediction_transformer():
    weather = _get_live_weather()
    cascade = evaluate_cascade_risk(weather)
    return cascade["predictions"]["transformer"]

@router.get("/predictions/chiller")
def get_prediction_chiller():
    weather = _get_live_weather()
    cascade = evaluate_cascade_risk(weather)
    return cascade["predictions"]["chiller"]

@router.get("/predictions/pump")
def get_prediction_pump():
    weather = _get_live_weather()
    cascade = evaluate_cascade_risk(weather)
    return cascade["predictions"]["pump"]

@router.get("/predictions/flood")
def get_prediction_flood():
    weather = _get_live_weather()
    cascade = evaluate_cascade_risk(weather)
    return cascade["predictions"]["flood"]

@router.get("/cascade/current")
@router.get("/risk/cascade")
def get_cascade_current():
    weather = _get_live_weather()
    cascade = evaluate_cascade_risk(weather)
    return {
        "success": True,
        "overall_risk": cascade["overall_risk"],
        "risk_level": cascade["level"],
        "confidence": cascade["confidence"],
        "drivers": cascade["drivers"],
        "equipment": cascade["affected_equipment"],
        "downstream_impacts": cascade["potential_downstream_impact"],
        "explanation": cascade["explanation"],
        "data_quality": cascade["data_quality"],
        "cascade_risk": cascade
    }

@router.get("/recommendations")
def get_ai_recommendations():
    weather = _get_live_weather()
    cascade = evaluate_cascade_risk(weather)
    rec = generate_recommendations(cascade)
    return {"success": True, "data_type": "AI RECOMMENDATION", "recommendations": rec}

@router.get("/model-health")
def get_model_health():
    report = get_model_health_report()
    return {"success": True, "models": report}

@router.post("/simulation/run")
def run_simulation_endpoint(
    scenario_key: str = Query("HEATWAVE"),
    payload: dict = Body(None)
):
    custom_params = payload.get("parameters") if payload else None
    result = run_simulation_scenario(scenario_key, custom_params)
    return {"success": True, "data_type": "SIMULATION", "simulation": result}

@router.get("/simulation/scenarios")
def get_simulation_scenarios():
    return {"success": True, "scenarios": SCENARIOS_PRESETS}

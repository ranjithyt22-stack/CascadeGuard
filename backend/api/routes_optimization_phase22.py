"""
backend/api/routes_optimization_phase22.py
===========================================
Phase 22 — Resilience Optimization & Prescriptive Action Planner Endpoints

Provides REST API endpoints for multi-attribute prescriptive action planning, strategy library lookup,
plan approval workflows, promotion to Phase 19 Incident Management, sensitivity analysis, and robustness testing.
"""

from fastapi import APIRouter, Path, Query, HTTPException, Body
from fastapi.responses import JSONResponse
import time
from typing import Dict, Any, List, Optional

import state
from services.intervention_library import intervention_library
from services.optimization_engine import optimization_engine
from services.prediction_engine import prediction_engine
from services.decision_engine import decision_engine


router = APIRouter()


@router.get("/optimization/strategies")
def get_strategies_endpoint():
    """Returns the centralized library of operational intervention strategies."""
    strats = intervention_library.get_all_strategies()
    return {"success": True, "count": len(strats), "strategies": strats}


@router.post("/optimization/optimize")
def optimize_response_endpoint(payload: Dict[str, Any] = Body(...)):
    """Executes prescriptive optimization across candidate intervention plans."""
    site_id = payload.get("site_id", "SITE-001")
    scenario_inputs = payload.get("scenario", payload.get("inputs", {}))
    if not scenario_inputs and "temperature" in payload:
        scenario_inputs = payload

    opt_record = optimization_engine.optimize_response(site_id, scenario_inputs)
    return {"success": True, "optimization": opt_record}


@router.post("/mitigation/projection")
def mitigation_projection_endpoint(payload: Dict[str, Any] = Body(...)):
    """Return an asset-specific, modelled mitigation projection for Decision Center."""
    site_id = payload.get("site_id")
    asset_type = str(payload.get("asset_type", "")).upper().replace(" ", "_")
    if not site_id:
        raise HTTPException(status_code=400, detail="site_id is required.")
    site = state.site_registry.get_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail=f"Site ID '{site_id}' not found in Site Registry.")
    if asset_type not in {"TRANSFORMER", "CHILLER", "WATER_PUMP"}:
        raise HTTPException(status_code=400, detail="Mitigation model not available for this asset.")

    weather = state.weather_client_inst.get_current_data(
        location=site.get("city"), latitude=site.get("latitude"), longitude=site.get("longitude"), site_id=site_id
    )["data"]
    prediction = prediction_engine.predict_facility_risk(site, weather)
    decisions = decision_engine.evaluate_facility_decisions(site, weather)
    equipment = prediction["equipment"].get(asset_type.lower())
    decision = next((d for d in decisions["decisions"] if d.get("equipment_type") == asset_type), None)
    if not equipment or not decision:
        raise HTTPException(status_code=422, detail="No preventive action available for the selected asset.")

    now = prediction["milestones"]["NOW"]
    plus_72 = prediction["milestones"]["72h"]
    risk_key = f"{asset_type.lower()}_risk"
    scenario = {
        "temperature": now["temperature"], "humidity": now["humidity"], "rainfall": now["rain"],
        "wind_speed": now["wind_speed"], "duration_hours": 6.0
    }
    try:
        projection = optimization_engine.project_asset_mitigation(
            site_id, asset_type, float(now[risk_key]), scenario, decision["action"]
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {
        "success": True,
        "source": "optimization_engine",
        "site_id": site_id,
        "asset_type": asset_type,
        "asset_id": equipment.get("equipment_id"),
        "baseline_risk": projection["baseline_risk"],
        "current_risk": round(float(now[risk_key]), 1),
        "projected_72h_risk": round(float(plus_72[risk_key]), 1),
        "recommended_action": decision.get("action"),
        "projected_risk": projection["projected_risk"],
        "risk_change": projection["risk_change"],
        "mitigation_status": projection["status"],
        "response_time": projection["response_time_minutes"],
        "objective_score": projection["objective_score"],
        "site": {key: site.get(key) for key in ("site_id", "site_name", "city", "latitude", "longitude")},
        "asset": {"asset_type": asset_type, "asset_id": equipment.get("equipment_id")},
        "recommendation": {key: decision.get(key) for key in ("action", "priority", "why", "action_priority_level")},
        "risk_context": {
            "current_risk": round(float(now[risk_key]), 1), "risk_72h": round(float(plus_72[risk_key]), 1),
            "climate_stress": now["climate_stress"], "temperature": now["temperature"],
            "forecast_temperature": plus_72["temperature"], "humidity": now["humidity"],
            "rainfall": now["rain"], "wind": now["wind_speed"], "natural_events": prediction["natural_events"],
            "shap_factors": prediction.get("shap_explanation", {}).get("factors", [])
        },
        "projection": projection
    }


@router.get("/optimization/history")
@router.get("/optimization/history/all")
def get_optimization_history_endpoint():
    """Lists audit history of all generated optimization plans."""
    records = optimization_engine.get_all_records()
    return {"success": True, "count": len(records), "records": records, "history": records}



@router.get("/optimization/{optimization_id}")
def get_optimization_record_endpoint(optimization_id: str = Path(...)):
    """Retrieves a specific optimization audit record by ID."""
    record = optimization_engine.get_optimization_record(optimization_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Optimization record {optimization_id} not found.")
    return {"success": True, "optimization": record}


@router.post("/optimization/{optimization_id}/approve")
def approve_plan_endpoint(optimization_id: str = Path(...), payload: Dict[str, Any] = Body(default={})):
    """Approves a recommended prescriptive action plan."""
    operator_name = payload.get("operator_name", "Shift Engineer")
    record = optimization_engine.approve_plan(optimization_id, operator_name)
    if not record:
        raise HTTPException(status_code=404, detail=f"Optimization record {optimization_id} not found.")
    return {"success": True, "optimization": record}


@router.post("/optimization/{optimization_id}/reject")
async def reject_plan_endpoint(optimization_id: str = Path(...), payload: Dict[str, Any] = Body(default={})):
    """Rejects a proposed prescriptive action plan with operator explanation."""
    reason = payload.get("reason", "Operator decision")
    record = optimization_engine.reject_plan(optimization_id, reason)
    if not record:
        raise HTTPException(status_code=404, detail=f"Optimization record {optimization_id} not found.")
    return {"success": True, "optimization": record}


@router.post("/optimization/{optimization_id}/promote")
def promote_plan_endpoint(optimization_id: str = Path(...)):
    """Promotes an approved action plan into the Phase 19 Incident Management System."""
    res = optimization_engine.promote_plan_to_incident(optimization_id)
    if not res or not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Unable to promote plan to Incident System."))
    return res


@router.post("/optimization/sensitivity")
def calculate_sensitivity_endpoint(payload: Dict[str, Any] = Body(...)):
    """Computes sensitivity analysis ranking stress variables by risk impact."""
    site_id = payload.get("site_id", "SITE-001")
    scenario_inputs = payload.get("scenario", payload.get("inputs", {}))
    sens = optimization_engine.calculate_sensitivity(site_id, scenario_inputs)
    return {"success": True, "site_id": site_id, "sensitivity": sens}


@router.post("/optimization/robustness")
def calculate_robustness_endpoint(payload: Dict[str, Any] = Body(...)):
    """Evaluates whether recommended plan remains optimal across temperature variations."""
    site_id = payload.get("site_id", "SITE-001")
    scenario_inputs = payload.get("scenario", payload.get("inputs", {}))
    rec_strat = payload.get("strategy_id", "COMBINED_RESILIENCE_PLAN")
    rob = optimization_engine.calculate_robustness(site_id, scenario_inputs, rec_strat)
    return {"success": True, "site_id": site_id, "robustness": rob}

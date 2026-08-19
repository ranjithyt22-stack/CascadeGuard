"""
backend/api/routes_prediction.py
================================
Phase 17 — Predictive Climate Risk & Facility Failure Forecasting Endpoints

Provides endpoints for facility climate risk prediction, weather risk forecasting,
equipment risk evaluation, predictive alerts, recommendations, and risk rankings.
Supports aliases under both /api/facilities/... and /api/sites/...
"""

from fastapi import APIRouter, Path, Query, HTTPException, Body
from fastapi.responses import JSONResponse
import time

import state
from services.prediction_engine import prediction_engine


router = APIRouter()


def _get_site_or_404(site_id: str):
    site = state.site_registry.get_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail=f"Site ID '{site_id}' not found in Site Registry.")
    return site


@router.get("/facilities/{site_id}/prediction")
@router.get("/sites/{site_id}/prediction")
@router.post("/facilities/{site_id}/prediction")
@router.post("/sites/{site_id}/prediction")
def get_facility_prediction(
    site_id: str = Path(...),
    scenario: str = Query(None),
    payload: dict = Body(default={})
):
    """GET/POST compatibility for the same facility prediction pipeline."""
    scenario = scenario or payload.get("scenario")
    site = _get_site_or_404(site_id)
    w_norm = state.weather_client_inst.get_current_data(
        location=site.get("city"),
        latitude=site.get("latitude"),
        longitude=site.get("longitude"),
        site_id=site_id
    )
    weather_full = w_norm["data"]
    res = prediction_engine.predict_facility_risk(site, weather_full, scenario_name=scenario)
    return {"success": True, "prediction": res}


@router.get("/facilities/{site_id}/risk")
@router.get("/sites/{site_id}/risk")
def get_facility_risk(site_id: str = Path(...)):
    site = _get_site_or_404(site_id)
    w_norm = state.weather_client_inst.get_current_data(
        location=site.get("city"),
        latitude=site.get("latitude"),
        longitude=site.get("longitude"),
        site_id=site_id
    )
    weather_full = w_norm["data"]
    res = prediction_engine.predict_facility_risk(site, weather_full)
    return {
        "success": True,
        "site_id": site_id,
        "site_name": site["site_name"],
        "overall_facility_risk": res["overall_facility_risk"],
        "risk_level": res["risk_level"],
        "climate_risk": res["climate_risk"],
        "climate_category": res["climate_category"],
        "trend": res["trend_analysis"]["trend"],
        "timestamp": res["timestamp"]
    }


@router.get("/facilities/{site_id}/forecast")
@router.get("/sites/{site_id}/forecast")
def get_facility_forecast(site_id: str = Path(...)):
    site = _get_site_or_404(site_id)
    w_norm = state.weather_client_inst.get_current_data(
        location=site.get("city"),
        latitude=site.get("latitude"),
        longitude=site.get("longitude"),
        site_id=site_id
    )
    weather_full = w_norm["data"]
    res = prediction_engine.predict_facility_risk(site, weather_full)
    return {
        "success": True,
        "site_id": site_id,
        "site_name": site["site_name"],
        "data_source": res["data_source"],
        "hourly_forecast": res["hourly_forecast"],
        "milestones": res["milestones"],
        "natural_events": res["natural_events"],
        "trend_analysis": res["trend_analysis"],
        "weather_summary": res["weather_summary"],
        "timestamp": res["timestamp"]
    }


@router.get("/facilities/{site_id}/equipment-risk")
@router.get("/sites/{site_id}/equipment-risk")
def get_facility_equipment_risk(site_id: str = Path(...)):
    site = _get_site_or_404(site_id)
    w_norm = state.weather_client_inst.get_current_data(
        location=site.get("city"),
        latitude=site.get("latitude"),
        longitude=site.get("longitude"),
        site_id=site_id
    )
    weather_full = w_norm["data"]
    res = prediction_engine.predict_facility_risk(site, weather_full)
    return {
        "success": True,
        "site_id": site_id,
        "site_name": site["site_name"],
        "equipment": res["equipment"],
        "timestamp": res["timestamp"]
    }


@router.get("/facilities/{site_id}/recommendations")
@router.get("/sites/{site_id}/recommendations")
def get_facility_recommendations(site_id: str = Path(...)):
    site = _get_site_or_404(site_id)
    w_norm = state.weather_client_inst.get_current_data(
        location=site.get("city"),
        latitude=site.get("latitude"),
        longitude=site.get("longitude"),
        site_id=site_id
    )
    weather_full = w_norm["data"]
    res = prediction_engine.predict_facility_risk(site, weather_full)
    return {
        "success": True,
        "site_id": site_id,
        "site_name": site["site_name"],
        "recommendations": res["recommendations"],
        "timestamp": res["timestamp"]
    }


@router.get("/predictive-alerts")
def get_predictive_alerts():
    all_sites = state.site_registry.get_all_sites(active_only=True)
    all_alerts = []
    for site in all_sites:
        w_norm = state.weather_client_inst.get_current_data(
            location=site.get("city"),
            latitude=site.get("latitude"),
            longitude=site.get("longitude"),
            site_id=site["site_id"]
        )
        res = prediction_engine.predict_facility_risk(site, w_norm["data"])
        all_alerts.extend(res["predictive_alerts"])

    # Sort alerts by severity (CRITICAL, HIGH, MODERATE, LOW, INFO)
    sev_order = {"CRITICAL": 0, "HIGH": 1, "MODERATE": 2, "LOW": 3, "INFO": 4}
    all_alerts.sort(key=lambda a: sev_order.get(a.get("severity", "LOW"), 5))

    return {
        "success": True,
        "count": len(all_alerts),
        "alerts": all_alerts,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }


@router.get("/facility-risk-ranking")
def get_facility_risk_ranking():
    all_sites = state.site_registry.get_all_sites()
    rankings = prediction_engine.generate_facility_risk_ranking(all_sites, state.weather_client_inst)
    return {
        "success": True,
        "count": len(rankings),
        "rankings": rankings,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }


@router.get("/maintenance-priorities")
def get_maintenance_priorities():
    all_sites = state.site_registry.get_all_sites()
    rankings = prediction_engine.generate_facility_risk_ranking(all_sites, state.weather_client_inst)
    priorities = prediction_engine.generate_maintenance_priorities(rankings)
    return {
        "success": True,
        "count": len(priorities),
        "priorities": priorities,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }


@router.get("/facilities/{site_id}/cascade")
@router.get("/sites/{site_id}/cascade")
def get_facility_cascade(site_id: str = Path(...), scenario: str = Query(None)):
    site = _get_site_or_404(site_id)
    w_norm = state.weather_client_inst.get_current_data(
        location=site.get("city"),
        latitude=site.get("latitude"),
        longitude=site.get("longitude"),
        site_id=site_id
    )
    weather_full = w_norm["data"]
    res = prediction_engine.predict_facility_risk(site, weather_full, scenario_name=scenario)
    
    from services.cascade_service import get_cascade_analysis
    cascade_res = get_cascade_analysis(site, weather_full, res)
    
    # If a specific scenario is requested, overwrite the top-level facility cascade fields to match the scenario
    if scenario and scenario != "NORMAL":
        scen_out = next((s for s in cascade_res["scenarios"] if s["scenario"].lower() == scenario.lower()), None)
        if scen_out:
            cascade_res["facility_cascade"]["current_risk"] = scen_out["cascade_risk"]
            cascade_res["facility_cascade"]["level"] = scen_out["level"]
            cascade_res["facility_cascade"]["dominant_source_asset"] = scen_out["source_asset"]
            cascade_res["facility_cascade"]["affected_asset_count"] = scen_out["affected_asset_count"]
            cascade_res["facility_cascade"]["maximum_depth"] = scen_out["maximum_depth"]

    return {
        "success": True,
        **cascade_res
    }


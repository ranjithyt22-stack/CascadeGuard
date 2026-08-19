"""
backend/api/routes_decision.py
===============================
Phase 18 — AI-Powered Climate Resilience Decision & Response Engine Endpoints

Provides endpoints for facility decision center, impact & urgency assessments,
multi-timeline response plans, action priorities, and operator action acknowledgements.
Supports aliases under both /api/facilities/... and /api/sites/...
"""

from fastapi import APIRouter, Path, Query, HTTPException, Body
from fastapi.responses import JSONResponse
import time
from typing import Dict, Any, Optional

import state
from services.decision_engine import decision_engine


router = APIRouter()


def _get_site_or_404(site_id: str):
    site = state.site_registry.get_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail=f"Site ID '{site_id}' not found in Site Registry.")
    return site


@router.get("/facilities/{site_id}/decisions")
@router.get("/sites/{site_id}/decisions")
def get_facility_decisions(site_id: str = Path(...)):
    site = _get_site_or_404(site_id)
    w_norm = state.weather_client_inst.get_current_data(
        location=site.get("city"),
        latitude=site.get("latitude"),
        longitude=site.get("longitude"),
        site_id=site_id
    )
    res = decision_engine.evaluate_facility_decisions(site, w_norm["data"])
    return {"success": True, "facility_decisions": res}


@router.get("/facilities/{site_id}/response-plan")
@router.get("/sites/{site_id}/response-plan")
def get_facility_response_plan(site_id: str = Path(...)):
    site = _get_site_or_404(site_id)
    w_norm = state.weather_client_inst.get_current_data(
        location=site.get("city"),
        latitude=site.get("latitude"),
        longitude=site.get("longitude"),
        site_id=site_id
    )
    res = decision_engine.evaluate_facility_decisions(site, w_norm["data"])
    return {
        "success": True,
        "site_id": site_id,
        "site_name": site["site_name"],
        "overall_risk": res["overall_risk"],
        "response_plan": res["response_plan"],
        "timestamp": res["timestamp"]
    }


@router.get("/facilities/{site_id}/actions")
@router.get("/sites/{site_id}/actions")
def get_facility_actions(
    site_id: str = Path(...),
    priority: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    site = _get_site_or_404(site_id)
    w_norm = state.weather_client_inst.get_current_data(
        location=site.get("city"),
        latitude=site.get("latitude"),
        longitude=site.get("longitude"),
        site_id=site_id
    )
    res = decision_engine.evaluate_facility_decisions(site, w_norm["data"])
    actions = res["decisions"]

    if priority:
        actions = [a for a in actions if a["priority"].upper() == priority.upper() or a["action_priority_level"].upper() == priority.upper()]
    if status:
        actions = [a for a in actions if a["status"].upper() == status.upper()]

    return {
        "success": True,
        "site_id": site_id,
        "count": len(actions),
        "actions": actions,
        "timestamp": res["timestamp"]
    }


@router.get("/decision-center")
def get_decision_center_summary():
    all_sites = state.site_registry.get_all_sites(active_only=True)
    all_decisions = []
    critical_cnt = 0
    urgent_cnt = 0
    high_cnt = 0
    moderate_cnt = 0

    for site in all_sites:
        w_norm = state.weather_client_inst.get_current_data(
            location=site.get("city"),
            latitude=site.get("latitude"),
            longitude=site.get("longitude"),
            site_id=site["site_id"]
        )
        res = decision_engine.evaluate_facility_decisions(site, w_norm["data"])
        all_decisions.append(res)

        for d in res["decisions"]:
            p = d.get("action_priority_level", d.get("priority", "LOW"))
            if p == "CRITICAL":
                critical_cnt += 1
            elif p == "URGENT":
                urgent_cnt += 1
            elif p == "HIGH":
                high_cnt += 1
            elif p == "MODERATE":
                moderate_cnt += 1

    # Sort facilities by facility_priority_score descending
    all_decisions.sort(key=lambda f: f["facility_priority_score"], reverse=True)
    top_facility = all_decisions[0] if all_decisions else None

    return {
        "success": True,
        "total_facilities": len(all_sites),
        "critical_actions": critical_cnt,
        "urgent_actions": urgent_cnt,
        "high_actions": high_cnt,
        "moderate_actions": moderate_cnt,
        "top_priority_facility": top_facility["site_name"] if top_facility else "N/A",
        "top_priority_site_id": top_facility["site_id"] if top_facility else "N/A",
        "top_action": top_facility["top_action"] if top_facility else None,
        "facility_rankings": [
            {
                "rank": i + 1,
                "site_id": f["site_id"],
                "site_name": f["site_name"],
                "city": f["city"],
                "overall_risk": f["overall_risk"],
                "facility_priority_score": f["facility_priority_score"],
                "priority_level": f["facility_priority_level"],
                "top_action": f["top_action"]["action"] if f["top_action"] else "None",
                "top_equipment": f["top_action"]["equipment_id"] if f["top_action"] else "None"
            }
            for i, f in enumerate(all_decisions)
        ],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }


@router.post("/decision-support")
def decision_support_endpoint(payload: Dict[str, Any] = Body(default={})):
    """Compatibility entry point that reuses the facility Decision Engine."""
    site_id = payload.get("site_id")
    if not site_id:
        return get_decision_center_summary()
    site = _get_site_or_404(site_id)
    weather = state.weather_client_inst.get_current_data(
        location=site.get("city"),
        latitude=site.get("latitude"),
        longitude=site.get("longitude"),
        site_id=site_id
    )["data"]
    return {"success": True, "facility_decisions": decision_engine.evaluate_facility_decisions(site, weather)}


@router.get("/action-priorities")
def get_all_action_priorities():
    all_sites = state.site_registry.get_all_sites(active_only=True)
    all_actions = []

    for site in all_sites:
        w_norm = state.weather_client_inst.get_current_data(
            location=site.get("city"),
            latitude=site.get("latitude"),
            longitude=site.get("longitude"),
            site_id=site["site_id"]
        )
        res = decision_engine.evaluate_facility_decisions(site, w_norm["data"])
        all_actions.extend(res["decisions"])

    all_actions.sort(key=lambda a: a["action_priority_score"], reverse=True)

    for i, a in enumerate(all_actions):
        a["rank"] = i + 1

    return {
        "success": True,
        "count": len(all_actions),
        "actions": all_actions,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }


@router.get("/response-summary")
def get_response_summary():
    return get_decision_center_summary()


@router.post("/actions/{action_id}/acknowledge")
def acknowledge_action_endpoint(action_id: str = Path(...)):
    ok = decision_engine.update_action_status(action_id, "ACKNOWLEDGED")
    if not ok:
        raise HTTPException(status_code=404, detail=f"Action ID '{action_id}' not found.")
    return {
        "success": True,
        "message": f"Action '{action_id}' acknowledged by operator.",
        "action_id": action_id,
        "status": "ACKNOWLEDGED",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }


@router.post("/actions/{action_id}/status")
def update_action_status_endpoint(
    action_id: str = Path(...),
    payload: Dict[str, Any] = Body(...)
):
    new_status = payload.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="Missing required field: status")

    ok = decision_engine.update_action_status(action_id, new_status)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Action ID '{action_id}' not found.")

    return {
        "success": True,
        "message": f"Action '{action_id}' status updated to {new_status.upper()}.",
        "action_id": action_id,
        "status": new_status.upper(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

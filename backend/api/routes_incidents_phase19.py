"""
backend/api/routes_incidents_phase19.py
=========================================
Phase 19 — Resilience Orchestration, Incident Management & Automated Alerting Endpoints

Provides REST API routes for incident management, status transitions, risk re-evaluation,
response effectiveness, timeline logs, notifications, and historical learning exports.
"""

from fastapi import APIRouter, Path, Query, HTTPException, Body
from fastapi.responses import JSONResponse
import time
from typing import Dict, Any, Optional

import state
from services.incident_engine_phase19 import incident_engine_p19
from services.response_effectiveness_engine import response_effectiveness_engine
from services.notification_engine import notification_engine
from services.incident_monitor import incident_monitor_p19


router = APIRouter()


@router.get("/incidents")
def get_incidents_list(
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    site_id: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    active_only: bool = Query(False)
):
    incidents = incident_engine_p19.get_all_incidents(active_only=active_only, site_id=site_id)

    if severity and severity.upper() != "ALL":
        incidents = [i for i in incidents if i.get("severity", "").upper() == severity.upper()]
    if status and status.upper() != "ALL":
        incidents = [i for i in incidents if i.get("status", "").upper() == status.upper()]
    if team and team.upper() != "ALL":
        incidents = [i for i in incidents if team.upper() in i.get("assigned_team", "").upper()]

    active_count = len([i for i in incidents if i.get("status", "").upper() in ["OPEN", "ACKNOWLEDGED", "STARTED"]])
    resolved_count = len([i for i in incidents if i.get("status", "").upper() in ["RESOLVED", "CLOSED", "MITIGATED"]])

    return {
        "success": True,
        "count": len(incidents),
        "incidents": incidents,
        "active_incidents_count": active_count,
        "resolved_incidents_count": resolved_count,
        "data": {
            "active_incidents": [i for i in incidents if i.get("status", "").upper() != "CLOSED"],
            "resolved_incidents": [i for i in incidents if i.get("status", "").upper() == "CLOSED"]
        },
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }


@router.get("/incident-summary")
def get_incident_summary_endpoint():
    kpis = incident_engine_p19.get_incident_summary_kpis()
    return {
        "success": True,
        "summary": kpis,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }


@router.get("/incident-history")
def get_incident_history_dataset():
    dataset = incident_engine_p19.export_learning_dataset()
    return {
        "success": True,
        "count": len(dataset),
        "dataset": dataset,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }


@router.post("/incidents/evaluate")
def evaluate_facilities_endpoint():
    res = incident_monitor_p19.evaluate_all_facilities()
    return res


@router.get("/incidents/{incident_id}")
def get_single_incident(incident_id: str = Path(...)):
    inc = incident_engine_p19.get_incident(incident_id.strip())
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident ID '{incident_id}' not found.")
    return {"success": True, "incident": inc}


@router.get("/incidents/{incident_id}/timeline")
def get_incident_timeline(incident_id: str = Path(...)):
    inc = incident_engine_p19.get_incident(incident_id.strip())
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident ID '{incident_id}' not found.")
    return {
        "success": True,
        "incident_id": incident_id,
        "timeline": inc.get("timeline", []),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }


@router.get("/incidents/{incident_id}/effectiveness")
def get_incident_effectiveness(incident_id: str = Path(...)):
    inc = incident_engine_p19.get_incident(incident_id.strip())
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident ID '{incident_id}' not found.")
    
    eff = inc.get("response_effectiveness")
    if not eff:
        return {
            "success": True,
            "incident_id": incident_id,
            "evaluated": False,
            "message": "Response effectiveness not evaluated yet. Complete operator action to trigger risk re-evaluation."
        }
    return {
        "success": True,
        "incident_id": incident_id,
        "evaluated": True,
        "effectiveness": eff
    }


@router.post("/incidents")
def create_incident_endpoint(payload: Dict[str, Any] = Body(...)):
    site_id = payload.get("site_id")
    equipment_id = payload.get("equipment_id")
    if not site_id or not equipment_id:
        raise HTTPException(status_code=400, detail="Missing site_id or equipment_id.")

    site = state.site_registry.get_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail=f"Site '{site_id}' not found.")

    # Evaluate decision engine for site & equipment
    w_norm = state.weather_client_inst.get_current_data(
        location=site.get("city"),
        latitude=site.get("latitude"),
        longitude=site.get("longitude"),
        site_id=site_id
    )
    from services.decision_engine import decision_engine
    dec_res = decision_engine.evaluate_facility_decisions(site, w_norm["data"])

    # Find matching equipment decision
    matched = None
    for d in dec_res.get("decisions", []):
        if d.get("equipment_id") == equipment_id or equipment_id.upper() in d.get("equipment_type", ""):
            matched = d
            break

    if not matched and dec_res.get("top_action"):
        matched = dec_res["top_action"]

    r_score = matched.get("risk_score", 50.0) if matched else 50.0
    p_score = matched.get("action_priority_score", 50.0) if matched else 50.0
    action = matched.get("action", "Inspect equipment") if matched else "Inspect equipment"
    why = matched.get("why", "Risk monitoring") if matched else "Risk monitoring"

    inc, is_new = incident_engine_p19.create_or_update_incident(
        site_id=site_id,
        site_name=site["site_name"],
        equipment_id=equipment_id,
        equipment_type=matched.get("equipment_type", "EQUIPMENT") if matched else "EQUIPMENT",
        risk_score=r_score,
        priority_score=p_score,
        impact_score=matched.get("impact_score", 50.0) if matched else 50.0,
        urgency_score=matched.get("urgency_score", 50.0) if matched else 50.0,
        recommended_action=action,
        reason=why,
        actor="Operator/API"
    )

    return {"success": True, "created": is_new, "incident": inc}


@router.patch("/incidents/{incident_id}/status")
def update_incident_status_endpoint(
    incident_id: str = Path(...),
    payload: Dict[str, Any] = Body(...)
):
    new_status = payload.get("status")
    notes = payload.get("notes")
    actor = payload.get("actor", "Operator")
    if not new_status:
        raise HTTPException(status_code=400, detail="Missing required field: status")

    ok, inc, msg = incident_engine_p19.update_incident_status(incident_id.strip(), new_status, actor=actor, notes=notes)
    if not ok:
        raise HTTPException(status_code=400 if inc else 404, detail=msg)

    return {"success": True, "message": msg, "incident": inc}


@router.post("/incidents/{incident_id}/acknowledge")
def acknowledge_incident_phase19(incident_id: str = Path(...)):
    ok, inc, msg = incident_engine_p19.update_incident_status(incident_id.strip(), "ACKNOWLEDGED", actor="Operator")
    if not ok:
        raise HTTPException(status_code=400 if inc else 404, detail=msg)
    return {"success": True, "message": msg, "incident": inc}


@router.post("/incidents/{incident_id}/start")
def start_action_phase19(incident_id: str = Path(...)):
    ok, inc, msg = incident_engine_p19.update_incident_status(incident_id.strip(), "IN_PROGRESS", actor="Operator")
    if not ok:
        raise HTTPException(status_code=400 if inc else 404, detail=msg)
    return {"success": True, "message": msg, "incident": inc}


@router.post("/incidents/{incident_id}/complete")
def complete_action_phase19(
    incident_id: str = Path(...),
    payload: Dict[str, Any] = Body(...)
):
    notes = payload.get("notes", "Operator action completed.")
    res = response_effectiveness_engine.evaluate_response_effectiveness(incident_id.strip(), operator_notes=notes)
    if not res.get("success"):
        raise HTTPException(status_code=404, detail=res.get("error", "Error evaluating response effectiveness."))
    return res


@router.post("/incidents/{incident_id}/resolve")
def resolve_incident_phase19(incident_id: str = Path(...)):
    ok, inc, msg = incident_engine_p19.update_incident_status(incident_id.strip(), "RESOLVED", actor="Operator")
    if not ok:
        raise HTTPException(status_code=400 if inc else 404, detail=msg)
    return {"success": True, "message": msg, "incident": inc}


@router.post("/incidents/{incident_id}/close")
def close_incident_phase19(incident_id: str = Path(...)):
    ok, inc, msg = incident_engine_p19.update_incident_status(incident_id.strip(), "CLOSED", actor="Operator")
    if not ok:
        raise HTTPException(status_code=400 if inc else 404, detail=msg)
    return {"success": True, "message": msg, "incident": inc}


@router.get("/notifications")
def get_notifications_endpoint(
    unread_only: bool = Query(False),
    site_id: Optional[str] = Query(None)
):
    notifs = notification_engine.get_all_notifications(unread_only=unread_only, site_id=site_id)
    unread_cnt = len([n for n in notification_engine.notifications if n["status"] == "UNREAD"])
    return {
        "success": True,
        "unread_count": unread_cnt,
        "count": len(notifs),
        "notifications": notifs,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }


@router.patch("/notifications/{notification_id}/read")
def mark_notification_read_endpoint(notification_id: str = Path(...)):
    ok = notification_engine.mark_as_read(notification_id.strip())
    if not ok:
        raise HTTPException(status_code=404, detail=f"Notification ID '{notification_id}' not found.")
    return {"success": True, "message": f"Notification '{notification_id}' marked as READ."}

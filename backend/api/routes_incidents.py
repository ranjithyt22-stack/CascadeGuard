"""
backend/api/routes_incidents.py
================================
Phase 13: Incident intelligence & alerting
- GET  /api/incidents
- GET  /api/incidents/{incident_id}
- POST /api/incidents/{incident_id}/acknowledge
- POST /api/incidents/{incident_id}/resolve
- POST /api/incidents/generate-report
- GET  /api/alerts/status
- POST /api/incidents/test-alert
"""
import io
import time
import traceback

from fastapi import APIRouter, Path, HTTPException
from fastapi.responses import StreamingResponse

import state
from report_generator import generate_pdf_report
from schemas.requests import GenerateReportRequest

router = APIRouter()


@router.get("/incidents")
def get_incidents_endpoint():
    data = state.incident_engine.get_all_incidents()
    return {
        "success": True,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "active_incidents_count": len(data.get("active_incidents", [])),
        "resolved_incidents_count": len(data.get("resolved_incidents", [])),
        "data": data
    }


@router.post("/incidents/generate-report")
def generate_incident_report_endpoint(body: GenerateReportRequest = GenerateReportRequest()):
    from api.routes_reports import build_pdf_streaming_response, _get_default_incident
    inc_id = body.incident_id if body else None
    inc = _get_default_incident(inc_id)
    fname = f"CascadeGuard_Incident_{inc_id}.pdf" if inc_id else "CascadeGuard_Incident_Report.pdf"
    return build_pdf_streaming_response(inc, fname)


@router.get("/alerts/status")
def alert_status_endpoint():
    return {"success": True, "alert_status": state.alert_manager.get_status()}


@router.post("/incidents/test-alert")
def test_alert_endpoint():
    try:
        sample_inc = {
            "incident_id": "INC-TEST-999",
            "severity": "CRITICAL",
            "system_risk": 82.4,
            "most_vulnerable_asset": "CHILLER",
            "trigger": "Manual API Webhook Test Trigger",
            "data_sources": {"climate": "LIVE_OPEN_METEO_API"}
        }
        res = state.alert_manager.dispatch_alert(sample_inc)
        return {"success": True, "dispatch_result": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/incidents/{incident_id}")
def get_single_incident_endpoint(incident_id: str = Path(...)):
    inc = state.incident_engine.get_incident_by_id(incident_id.strip())
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident ID '{incident_id}' not found")
    return {"success": True, "incident": inc}


@router.post("/incidents/{incident_id}/acknowledge")
def acknowledge_incident_endpoint(incident_id: str = Path(...)):
    is_ok, inc = state.incident_engine.acknowledge_incident(incident_id.strip())
    if not is_ok:
        raise HTTPException(status_code=404, detail=f"Incident ID '{incident_id}' not found")
    return {
        "success": True,
        "message": f"Incident '{incident_id}' acknowledged successfully",
        "incident": inc
    }


@router.post("/incidents/{incident_id}/resolve")
def resolve_incident_endpoint(incident_id: str = Path(...)):
    is_ok, inc = state.incident_engine.resolve_incident(incident_id.strip())
    if not is_ok:
        raise HTTPException(status_code=404, detail=f"Incident ID '{incident_id}' not found")
    return {
        "success": True,
        "message": f"Incident '{incident_id}' resolved successfully",
        "incident": inc
    }

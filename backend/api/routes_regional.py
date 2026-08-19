"""
backend/api/routes_regional.py
================================
Phase 14: Regional command center aggregation
- GET /api/regional-status
- GET /api/regional/incidents
- GET /api/regional-history
"""
import time
from fastapi import APIRouter, Query, HTTPException

import state

router = APIRouter()


@router.get("/regional-status")
def regional_status_endpoint():
    active_sites = state.site_registry.get_all_sites(active_only=True)
    from state import analyze_site_internal
    site_evals = []
    for s in active_sites:
        try:
            ev = analyze_site_internal(s["site_id"])
            site_evals.append(ev)
        except Exception as e:
            print(f"Error analyzing site {s['site_id']}:", e)

    regional_eval = state.regional_risk_engine.evaluate_regional_status(site_evals)
    return {"success": True, "regional": regional_eval}


@router.get("/regional/incidents")
def regional_incidents_endpoint(
    severity: str = Query(None),
    site_id: str = Query(None),
    status: str = Query(None)
):
    all_incidents = state.incident_engine.get_incidents()
    history = all_incidents.get("history", [])

    filtered = history
    if severity:
        filtered = [i for i in filtered if i.get("severity") == severity.upper()]
    if site_id:
        filtered = [i for i in filtered if i.get("site_id") == site_id]
    if status:
        filtered = [i for i in filtered if i.get("status") == status.upper()]

    return {"success": True, "count": len(filtered), "incidents": filtered}


@router.get("/regional-history")
def regional_history_endpoint():
    history = state.regional_risk_engine.get_history()
    return {"success": True, "count": len(history), "history": history}

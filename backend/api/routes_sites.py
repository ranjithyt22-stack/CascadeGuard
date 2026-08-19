"""
backend/api/routes_sites.py
============================
Phase 14: Multi-site regional command center CRUD
- GET    /api/sites
- POST   /api/sites   (→ 201)
- GET    /api/sites/{site_id}
- PUT    /api/sites/{site_id}
- DELETE /api/sites/{site_id}
- POST   /api/sites/{site_id}/activate
- POST   /api/sites/{site_id}/deactivate
- GET    /api/sites/{site_id}/analyze
"""
from fastapi import APIRouter, Path, Query, HTTPException
from fastapi.responses import JSONResponse

import state
from schemas.requests import SiteCreateRequest, SiteUpdateRequest

router = APIRouter()


@router.get("/sites")
def get_sites():
    sites = state.site_registry.get_all_sites()
    return {"success": True, "count": len(sites), "sites": sites}


@router.post("/sites", status_code=201)
def create_site(body: SiteCreateRequest):
    req_data = body.model_dump()
    ok, msg, new_site = state.site_registry.add_site(req_data)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg, "site": new_site}


@router.get("/sites/{site_id}/climate")
def get_site_climate_endpoint(site_id: str = Path(...)):
    from api.routes_climate import climate_intelligence_endpoint
    return climate_intelligence_endpoint(site_id=site_id)


@router.get("/sites/{site_id}/analyze")
def site_analyze_endpoint(site_id: str = Path(...), scenario: str = Query(None)):
    from state import analyze_site_internal
    site = state.site_registry.get_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail=f"Site '{site_id}' not found.")
    return analyze_site_internal(site_id, scenario_name=scenario)


@router.post("/sites/{site_id}/activate")
def activate_site_endpoint(site_id: str = Path(...)):
    ok, msg = state.site_registry.activate_site(site_id)
    if not ok:
        raise HTTPException(status_code=404, detail=msg)
    return {"success": True, "message": msg}


@router.post("/sites/{site_id}/deactivate")
def deactivate_site_endpoint(site_id: str = Path(...)):
    ok, msg = state.site_registry.deactivate_site(site_id)
    if not ok:
        raise HTTPException(status_code=404, detail=msg)
    return {"success": True, "message": msg}


@router.get("/sites/{site_id}")
def get_site_details(site_id: str = Path(...)):
    site = state.site_registry.get_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail=f"Site '{site_id}' not found.")
    return {"success": True, "site": site}


@router.put("/sites/{site_id}")
def update_site_endpoint(site_id: str = Path(...), body: SiteUpdateRequest = None):
    req_data = body.model_dump(exclude_none=True) if body else {}
    ok, msg, updated_site = state.site_registry.update_site(site_id, req_data)
    if not ok:
        status_code = 404 if "not found" in msg.lower() else 400
        raise HTTPException(status_code=status_code, detail=msg)
    return {"success": True, "message": msg, "site": updated_site}


@router.delete("/sites/{site_id}")
def delete_site_endpoint(site_id: str = Path(...)):
    ok, msg = state.site_registry.delete_site(site_id)
    if not ok:
        raise HTTPException(status_code=404, detail=msg)
    return {"success": True, "message": msg}

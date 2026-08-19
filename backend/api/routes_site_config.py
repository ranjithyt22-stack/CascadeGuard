"""
backend/api/routes_site_config.py
==================================
Phase 11A: Precise site location & single-site active configuration
- POST /api/site/configure
- GET  /api/site/config
"""
from fastapi import APIRouter, HTTPException
from site_config import validate_site_config, get_active_site_config, set_active_site_config
from schemas.requests import SiteConfigureRequest

router = APIRouter()


@router.post("/site/configure")
def site_configure_endpoint(body: SiteConfigureRequest):
    try:
        data = body.model_dump()
        is_ok, err_msg, norm_site = validate_site_config(data)
        if not is_ok:
            raise HTTPException(status_code=400, detail=err_msg)
        set_active_site_config(norm_site)
        return {"success": True, "site": norm_site}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/site/config")
def site_config_endpoint():
    site = get_active_site_config()
    if not site:
        raise HTTPException(status_code=404, detail="No site configured")
    return {"success": True, "configured": True, "site": site}

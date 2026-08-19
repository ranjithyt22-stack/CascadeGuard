"""
backend/api/routes_reports.py
==============================
FastAPI endpoints for executive, regional, fleet, and incident PDF report generation and download.
Ensures proper PDF header validation (%PDF-), Content-Type (application/pdf),
and non-UUID Content-Disposition filename headers.
"""
import io
import time
import traceback
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

import state
from report_generator import generate_pdf_report
from schemas.requests import GenerateReportRequest

router = APIRouter()


def _get_default_incident(inc_id: Optional[str] = None) -> dict:
    if inc_id:
        found = state.incident_engine.get_incident_by_id(inc_id.strip())
        if found:
            return found

    all_inc = state.incident_engine.get_all_incidents()
    active_list = all_inc.get("active_incidents", [])
    history_list = all_inc.get("history", [])

    if active_list:
        return active_list[0]
    if history_list:
        return history_list[0]

    return {
        "incident_id": inc_id or "INC-2026-DEMO-001",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "severity": "WARNING",
        "status": "OPEN",
        "system_risk": 55.4,
        "most_vulnerable_asset": "CHILLER",
        "affected_assets": {
            "transformer_risk": 42.0,
            "chiller_risk": 68.0,
            "water_pump_risk": 35.0
        },
        "trigger": "Executive Risk Report",
        "cascade_path": "Climate Stress -> Water Pump -> Chiller -> Transformer -> System Cascade Risk",
        "data_sources": {
            "climate": "LIVE_OPEN_METEO_API",
            "transformer": "HISTORICAL_REPLAY",
            "chiller": "HISTORICAL_DATASET",
            "water_pump": "HISTORICAL_DATASET (DECISION SUPPORT ONLY)"
        }
    }


def build_pdf_streaming_response(incident_dict: dict, filename: str):
    try:
        pdf_bytes = generate_pdf_report(incident_dict)

        # 1. Verify buffer non-empty
        if not pdf_bytes or len(pdf_bytes) == 0:
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Generated PDF report buffer is empty"}
            )

        # 2. Verify starts with %PDF-
        if not pdf_bytes.startswith(b"%PDF-"):
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Generated report is invalid (does not start with %PDF- header)"}
            )

        # 3. Ensure filename format
        if not filename.lower().endswith(".pdf"):
            filename = f"{filename}.pdf"

        headers = {
            "Content-Type": "application/pdf",
            "Content-Disposition": f'attachment; filename="{filename}"'
        }

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers=headers
        )
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"PDF generation failed: {str(e)}"}
        )


@router.post("/reports/executive")
@router.get("/reports/executive")
def get_executive_report_endpoint():
    inc = _get_default_incident()
    return build_pdf_streaming_response(inc, "CascadeGuard_Executive_Report.pdf")


@router.post("/reports/regional")
@router.get("/reports/regional")
def get_regional_report_endpoint():
    inc = _get_default_incident()
    return build_pdf_streaming_response(inc, "CascadeGuard_Regional_Report.pdf")


@router.post("/reports/fleet")
@router.get("/reports/fleet")
def get_fleet_report_endpoint():
    inc = _get_default_incident()
    return build_pdf_streaming_response(inc, "CascadeGuard_Fleet_Report.pdf")


@router.post("/reports/incident")
@router.get("/reports/incident")
def get_incident_report_endpoint(incident_id: Optional[str] = Query(None)):
    inc = _get_default_incident(incident_id)
    fname = f"CascadeGuard_Incident_{incident_id}.pdf" if incident_id else "CascadeGuard_Incident_Report.pdf"
    return build_pdf_streaming_response(inc, fname)

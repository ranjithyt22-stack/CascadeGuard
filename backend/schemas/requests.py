"""
backend/schemas/requests.py
===========================
Pydantic v2 request-body models for CascadeGuard FastAPI endpoints.
All fields are optional where the Flask equivalent used .get() with defaults.
"""
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """POST /api/analyze — backward-compatible free-form telemetry payload."""
    location: str = "Coimbatore"
    # Allow any additional transformer/health telemetry fields
    model_config = {"extra": "allow"}


class SimulateScenarioRequest(BaseModel):
    """POST /api/simulate-scenario"""
    scenario: str = "NORMAL"
    tx_id: str = "TX-001"
    location: str = "Coimbatore"


class ScenarioAnalyzeRequest(BaseModel):
    """POST /api/scenario-analyze"""
    scenario: str = "HEATWAVE"
    location: str = "Coimbatore"
    tx_id: str = "TX-001"


class TelemetryModeRequest(BaseModel):
    """POST /api/telemetry/mode"""
    mode: str = Field(..., description="MOCK or REAL_OT")


class TelemetryScenarioRequest(BaseModel):
    """POST /api/telemetry/scenario"""
    scenario: str = Field(..., description="NORMAL | HIGH_LOAD | HEAT_STRESS | CHILLER_OVERLOAD | PUMP_DEGRADATION | COMBINED_CASCADE")


class SiteConfigureRequest(BaseModel):
    """POST /api/site/configure — single-site active configuration"""
    site_id: str = ""
    site_name: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    transformer_id: str = ""
    chiller_id: str = ""
    water_pump_id: str = ""


class SiteCreateRequest(BaseModel):
    """POST /api/sites — create a new regional site"""
    site_id: str
    site_name: str
    city: str
    latitude: float
    longitude: float
    transformer_id: Optional[str] = "TR-001"
    chiller_id: Optional[str] = "CH-001"
    water_pump_id: Optional[str] = "WP-001"
    model_config = {"extra": "allow"}


class SiteUpdateRequest(BaseModel):
    """PUT /api/sites/{site_id}"""
    site_name: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    transformer_id: Optional[str] = None
    chiller_id: Optional[str] = None
    water_pump_id: Optional[str] = None
    model_config = {"extra": "allow"}


class GenerateReportRequest(BaseModel):
    """POST /api/incidents/generate-report"""
    incident_id: Optional[str] = None


class MultiAssetAnalyzeRequest(BaseModel):
    """POST /api/multi-asset-analyze"""
    site_id: Optional[str] = None
    scenario: Optional[str] = None
    location: Optional[str] = None
    tx_id: Optional[str] = None


class RealtimeAnalyzeRequest(BaseModel):
    """POST /api/realtime-analyze"""
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    tx_id: Optional[str] = None

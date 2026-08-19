"""
backend/schemas/responses.py
============================
Shared Pydantic response models (kept minimal — most endpoints return
raw dicts via JSONResponse for 1-to-1 Flask response compatibility).
"""
from typing import Any, Optional
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    operational_model_version: str
    shap_explainer: str
    scenarios_available: int
    predictive_forecasting: str
    transformers_monitored: int


class SuccessResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str

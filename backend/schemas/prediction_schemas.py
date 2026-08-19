"""
backend/schemas/prediction_schemas.py
======================================
Unified Prediction Contract & Pydantic Schemas for CascadeGuard Platform (Phase I)
"""
from typing import Any, List, Optional, Dict
from pydantic import BaseModel, Field

class UnifiedPredictionResponse(BaseModel):
    model_id: str = Field(..., description="Unique machine learning model identifier")
    model_version: str = Field(..., description="Active production model version")
    prediction_timestamp: str = Field(..., description="ISO 8601 UTC timestamp of inference execution")
    horizon: str = Field(..., description="Target prediction horizon e.g. 1h, 6h, 24h, 72h, 15m, 60m")
    prediction: Any = Field(..., description="Primary prediction output (numeric value, class label, or forecast dict)")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Normalized risk score between 0.0 and 1.0")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model prediction confidence score between 0.0 and 1.0")
    status: str = Field(..., description="Operational status: NORMAL, WATCH, WARNING, CRITICAL, DECISION_SUPPORT_ONLY")
    contributors: List[str] = Field(default_factory=list, description="Top risk driver features contributing to prediction")
    data_quality: str = Field(..., description="Data quality metric: GOOD, DEGRADED, or INSUFFICIENT")
    data_quality_details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata on feature availability, telemetry age, missing values")

class ModelHealthItem(BaseModel):
    model_name: str
    model_id: str
    version: str
    training_date: str
    metrics: Dict[str, Any]
    status: str  # READY, DECISION_SUPPORT_ONLY, DEGRADED, OFFLINE
    confidence: float
    data_availability: str
    last_inference: str
    inference_latency_ms: float

class ModelHealthResponse(BaseModel):
    success: bool
    timestamp: str
    models: List[ModelHealthItem]

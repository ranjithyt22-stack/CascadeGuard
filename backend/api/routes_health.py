"""
backend/api/routes_health.py
============================
GET /api/health
"""
from fastapi import APIRouter
import state
from live_data import get_transformers

router = APIRouter()


@router.get("/health")
def health():
    return {
        "status": "online",
        "service": "CascadeGuard AI Command Center",
        "operational_model_version": state.operational_model_version,
        "shap_explainer": "active" if state.shap_explainer is not None else "inactive",
        "scenarios_available": 8,
        "predictive_forecasting": "active",
        "transformers_monitored": len(get_transformers())
    }

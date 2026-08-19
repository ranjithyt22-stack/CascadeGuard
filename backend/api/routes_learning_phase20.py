"""
backend/api/routes_learning_phase20.py
======================================
Phase 20 — Continuous Learning, Adaptive AI & Predictive Maintenance Intelligence Endpoints

Provides REST API routes for AI Learning summary, data health, facility/equipment baselines,
statistical anomaly detection, ML eligibility, model training, activation, rollback, and data export.
"""

from fastapi import APIRouter, Path, Query, HTTPException, Body
from fastapi.responses import JSONResponse
import time
from typing import Dict, Any, Optional

from services.learning_engine import learning_engine
from services.historical_analytics_engine import historical_analytics_engine
from services.anomaly_detection_engine import anomaly_detection_engine
from services.ml_training_engine import ml_training_engine
from services.model_registry import model_registry
from services.recommendation_learning_engine import recommendation_learning_engine
from services.incident_engine_phase19 import incident_engine_p19


router = APIRouter()


@router.get("/learning/summary")
def get_learning_summary_endpoint():
    return learning_engine.get_learning_summary()


@router.get("/learning/data-quality")
def get_data_quality_endpoint():
    return {
        "success": True,
        "data_health": historical_analytics_engine.validate_data_quality(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }


@router.get("/learning/facilities")
def get_facility_baselines_endpoint():
    return {
        "success": True,
        "facilities": historical_analytics_engine.get_facility_baselines(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }


@router.get("/learning/equipment")
def get_equipment_baselines_endpoint():
    return {
        "success": True,
        "equipment": historical_analytics_engine.get_equipment_baselines(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }


@router.get("/learning/anomalies")
def get_anomalies_endpoint():
    anomalies = anomaly_detection_engine.detect_all_anomalies()
    return {
        "success": True,
        "count": len(anomalies),
        "anomalies": anomalies,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }


@router.get("/learning/insights")
def get_learning_insights_endpoint():
    return {
        "success": True,
        "insights": learning_engine.generate_explainable_insights(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }


@router.get("/learning/eligibility")
def get_ml_eligibility_endpoint():
    return {
        "success": True,
        "eligibility": ml_training_engine.check_eligibility(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }


@router.get("/learning/interventions")
def get_intervention_rankings_endpoint(
    climate_driver: str = Query("HEAT"),
    equipment_type: str = Query("TRANSFORMER")
):
    rankings = recommendation_learning_engine.get_learned_recommendations(climate_driver, equipment_type)
    return {
        "success": True,
        "climate_driver": climate_driver,
        "equipment_type": equipment_type,
        "rankings": rankings,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }


@router.get("/learning/models")
def get_registered_models_endpoint():
    models = model_registry.get_all_models()
    active = model_registry.get_active_model()
    return {
        "success": True,
        "active_model_id": active["model_id"] if active else None,
        "count": len(models),
        "models": models,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }


@router.get("/learning/models/{model_id}")
def get_single_model_endpoint(model_id: str = Path(...)):
    m = model_registry.models.get(model_id.strip())
    if not m:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found in registry.")
    return {"success": True, "model": m}


@router.post("/learning/train")
def train_model_endpoint(payload: Dict[str, Any] = Body(default={})):
    model_type = payload.get("model_type", "RandomForest")
    force = payload.get("force", False)

    res = ml_training_engine.train_and_evaluate_model(model_type=model_type, force_train=force)
    if not res.get("success"):
        return JSONResponse(status_code=400, content=res)
    return res


@router.post("/learning/activate-model")
def activate_model_endpoint(payload: Dict[str, Any] = Body(...)):
    model_id = payload.get("model_id")
    if not model_id:
        raise HTTPException(status_code=400, detail="Missing required parameter: model_id")

    ok = model_registry.activate_model(model_id.strip(), actor="Operator/API")
    if not ok:
        raise HTTPException(status_code=404, detail=f"Model ID '{model_id}' not found in registry.")

    return {
        "success": True,
        "message": f"Model '{model_id}' activated successfully.",
        "active_model": model_registry.get_active_model()
    }


@router.post("/learning/rollback-model")
def rollback_model_endpoint():
    prev = model_registry.rollback_model(actor="Operator/API")
    if not prev:
        raise HTTPException(status_code=400, detail="No previous validated/retired model available for rollback.")

    return {
        "success": True,
        "message": f"Model rolled back to '{prev['model_id']}'.",
        "active_model": prev
    }


@router.get("/learning/export")
def export_learning_dataset_endpoint():
    dataset = incident_engine_p19.export_learning_dataset()
    return {
        "success": True,
        "count": len(dataset),
        "dataset": dataset,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

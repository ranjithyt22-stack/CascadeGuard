"""
backend/api/routes_realtime.py
==============================
Phase 10: real-time API adapter status & analysis
- GET  /api/realtime-status
- GET  /api/live   (alias)
- GET|POST /api/realtime-analyze
- GET|POST /api/multi-asset-analyze
"""
import time
import numpy as np
import pandas as pd
from fastapi import APIRouter, Query, HTTPException

import state
from state import (
    predict_health, predict_operational, risk_level, analyze_site_internal
)
from live_data import get_live_data
from cascade_graph import (
    evaluate_cascade_graph, build_transformer_asset_schema,
    build_chiller_asset_schema, build_water_pump_asset_schema
)
from climate_intelligence import analyze_climate_intelligence
from site_config import get_active_site_config
from schemas.requests import MultiAssetAnalyzeRequest, RealtimeAnalyzeRequest

router = APIRouter()


# ── shared chiller/pump prediction helper ─────────────────────────────────────

def _predict_chiller(chiller_sample: dict):
    chiller_risk  = 5.0
    prob_normal   = 0.95
    pred_class    = 1
    prob_dict     = {f"Class_{i}": 0.05 for i in range(1, 9)}
    prob_dict["Class_1"] = 0.95
    chiller_level = "NORMAL"

    if state.chiller_model is not None and state.chiller_features:
        ch_vals = [float(chiller_sample.get(feat, 0.0)) for feat in state.chiller_features]
        ch_X = pd.DataFrame([ch_vals], columns=state.chiller_features)
        ch_proba = state.chiller_model.predict_proba(ch_X)[0]
        normal_idx = int(state.chiller_mapping.get("normal_class_index", 0))
        prob_normal = float(ch_proba[normal_idx])
        pred_class_idx = int(np.argmax(ch_proba))
        pred_class = int(state.chiller_mapping.get("reverse_label_mapping", {}).get(str(pred_class_idx), pred_class_idx + 1))
        chiller_risk  = round(float((1.0 - prob_normal) * 100.0), 2)
        chiller_level = risk_level(chiller_risk)
        for i, p in enumerate(ch_proba):
            orig_l = state.chiller_mapping.get("reverse_label_mapping", {}).get(str(i), i + 1)
            prob_dict[f"Class_{orig_l}"] = round(float(p), 4)

    return chiller_risk, pred_class, prob_normal, prob_dict, chiller_level


def _predict_pump(pump_sample: dict):
    pump_risk  = 15.0
    pred_state = "NORMAL"
    pump_level = "LOW"

    if state.water_pump_model is not None and state.water_pump_features:
        p_vals = [float(pump_sample.get(feat, 0.0)) for feat in state.water_pump_features]
        p_X = pd.DataFrame([p_vals], columns=state.water_pump_features)
        try:
            p_proba    = state.water_pump_model.predict_proba(p_X)[0]
            pump_risk  = round(float((p_proba[1]*0.33 + p_proba[2]*0.66 + p_proba[3]*1.00) * 100.0), 2)
            state_idx  = int(np.argmax(p_proba))
            state_map  = {0: "NORMAL", 1: "WATCH", 2: "WARNING", 3: "CRITICAL"}
            pred_state = state_map.get(state_idx, "NORMAL")
        except Exception:
            pump_risk = 20.0

    return pump_risk, pred_state, pump_level


# ── GET /api/realtime-status ──────────────────────────────────────────────────

@router.get("/realtime-status")
def realtime_status_endpoint(site_id: str = Query(None)):
    site_info = state.site_registry.get_site(site_id) if site_id else None
    if site_info:
        site_cfg = site_info
        location = site_info.get("city") or site_info.get("site_name")
        lat = site_info.get("latitude")
        lon = site_info.get("longitude")
    else:
        site_cfg = get_active_site_config()
        location = site_cfg["location"]["name"]
        lat = site_cfg["location"]["latitude"]
        lon = site_cfg["location"]["longitude"]

    w_norm = state.weather_client_inst.get_current_data(
        location=location,
        latitude=lat,
        longitude=lon,
        site_id=site_id or "SITE-001"
    )
    intel = analyze_climate_intelligence(w_norm["data"], site_cfg)

    return {
        "success": True,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "site": site_cfg,
        "weather": state.weather_client_inst.get_status(),
        "transformer": state.transformer_client_inst.get_status(),
        "chiller": state.chiller_client_inst.get_status(),
        "water_pump": state.water_pump_client_inst.get_status(),
        "climate_intelligence": intel
    }


# ── GET /api/live (alias) ─────────────────────────────────────────────────────
@router.get("/live")
def live_alias_endpoint():
    return realtime_status_endpoint()


# ── GET|POST /api/realtime-analyze ───────────────────────────────────────────

def _do_realtime_analyze(location, lat, lon, tx_id, site_cfg) -> dict:
    # 1. Weather
    weather_normalized = state.weather_client_inst.get_current_data(
        location=location, latitude=lat, longitude=lon
    )
    climate_data = weather_normalized["data"]

    # 2. Transformer
    tx_sample = get_live_data(tx_id)
    tx_normalized = state.transformer_client_inst.get_current_data(tx_id=tx_id, replay_sample=tx_sample)
    mod_v3_op  = tx_sample.get("data_v3", tx_sample.get("data", {}))
    mod_health = tx_sample.get("health_data", {})
    health_idx, health_rk = predict_health(mod_health)
    op_rk = predict_operational(mod_v3_op)
    tx_health_contrib  = round(health_rk * 0.40, 2)
    tx_op_contrib      = round(op_rk * 0.40, 2)
    tx_climate_contrib = round(climate_data.get("climate_stress", 19.7) * 0.20, 2)
    tx_cascade_risk    = float(np.clip(tx_health_contrib + tx_op_contrib + tx_climate_contrib, 0, 100))
    tx_level           = risk_level(tx_cascade_risk)
    transformer_schema = build_transformer_asset_schema(tx_cascade_risk, health_rk, op_rk, tx_level)
    transformer_schema["provenance"] = tx_normalized["source"]
    transformer_schema["freshness"]  = tx_normalized["quality"]

    # 3. Chiller
    chiller_sample_dict = {}
    if state.chiller_df is not None and len(state.chiller_df) > 0:
        s_idx = int(time.time() // 5) % len(state.chiller_df)
        chiller_sample_dict = state.chiller_df.iloc[s_idx].to_dict()
    chiller_normalized = state.chiller_client_inst.get_current_data(chiller_sample=chiller_sample_dict)
    ch_risk, ch_pred, ch_prob_n, ch_prob_d, ch_level = _predict_chiller(chiller_sample_dict)
    chiller_schema = build_chiller_asset_schema(ch_risk, ch_pred, ch_prob_n, ch_prob_d, ch_level)
    chiller_schema["provenance"] = chiller_normalized["source"]
    chiller_schema["freshness"]  = chiller_normalized["quality"]

    # 4. Water Pump
    pump_sample_dict = {}
    if state.water_pump_df is not None and len(state.water_pump_df) > 0:
        s_idx = int(time.time() // 5) % len(state.water_pump_df)
        pump_sample_dict = state.water_pump_df.iloc[s_idx].to_dict()
    pump_normalized = state.water_pump_client_inst.get_current_data(pump_sample=pump_sample_dict)
    p_risk, p_state, p_level = _predict_pump(pump_sample_dict)
    pump_schema = build_water_pump_asset_schema(p_risk, p_state, p_level)
    pump_schema["provenance"] = pump_normalized["source"]
    pump_schema["freshness"]  = pump_normalized["quality"]

    # 5. Cascade
    cascade_eval = evaluate_cascade_graph(transformer_schema, chiller_schema, pump_schema, climate_data)
    intel        = analyze_climate_intelligence(climate_data, site_cfg)

    return {
        "success": True,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "site": site_cfg,
        "climate_intelligence": intel,
        "data_sources": {
            "weather": state.weather_client_inst.get_status(),
            "transformer": state.transformer_client_inst.get_status(),
            "chiller": state.chiller_client_inst.get_status(),
            "water_pump": state.water_pump_client_inst.get_status()
        },
        "assets": {
            "transformer": transformer_schema,
            "chiller": chiller_schema,
            "water_pump": pump_schema
        },
        "climate": climate_data,
        "system": cascade_eval["system"],
        "vulnerability": {
            "most_vulnerable_asset": cascade_eval["cascade"]["most_vulnerable_asset"]["asset"],
            "vulnerability_score": cascade_eval["cascade"]["most_vulnerable_asset"]["risk"],
            "details": cascade_eval["cascade"]["most_vulnerable_asset"]
        },
        "cascade_scenario": cascade_eval["cascade"],
        "recommendation": cascade_eval["recommendation"]
    }


@router.get("/realtime-analyze")
def realtime_analyze_get(
    location: str = Query(None),
    latitude: float = Query(None),
    longitude: float = Query(None),
    tx_id: str = Query(None)
):
    try:
        site_cfg = get_active_site_config()
        location = location or site_cfg["location"]["name"]
        latitude = latitude or site_cfg["location"]["latitude"]
        longitude = longitude or site_cfg["location"]["longitude"]
        tx_id    = tx_id or site_cfg["assets"]["transformer_id"]
        return _do_realtime_analyze(location, latitude, longitude, tx_id, site_cfg)
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/realtime-analyze")
def realtime_analyze_post(body: RealtimeAnalyzeRequest):
    try:
        site_cfg = get_active_site_config()
        location = body.location or site_cfg["location"]["name"]
        lat      = body.latitude or site_cfg["location"]["latitude"]
        lon      = body.longitude or site_cfg["location"]["longitude"]
        tx_id    = body.tx_id or site_cfg["assets"]["transformer_id"]
        return _do_realtime_analyze(location, lat, lon, tx_id, site_cfg)
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ── GET|POST /api/multi-asset-analyze ────────────────────────────────────────

@router.get("/multi-asset-analyze")
def multi_asset_analyze_get(
    site_id: str = Query(None),
    scenario: str = Query(None),
    location: str = Query(None),
    tx_id: str = Query(None)
):
    try:
        sid = site_id or get_active_site_config().get("site_id", "SITE-001")
        return analyze_site_internal(sid, scenario_name=scenario)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/multi-asset-analyze")
def multi_asset_analyze_post(body: MultiAssetAnalyzeRequest):
    try:
        sid = body.site_id or get_active_site_config().get("site_id", "SITE-001")
        return analyze_site_internal(sid, scenario_name=body.scenario)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

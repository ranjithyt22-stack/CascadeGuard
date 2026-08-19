"""
backend/api/routes_scenarios.py
===============================
GET /api/scenarios
GET|POST /api/scenario-analyze
GET /api/scenario-summary
"""
import time
import numpy as np
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse

import state
from state import (
    predict_health, predict_operational, get_climate, risk_level,
    analyze_site_internal
)
from live_data import get_live_data
from scenarios import get_available_scenarios, apply_scenario
from cascade_graph import (
    evaluate_cascade_scenario, build_transformer_asset_schema,
    build_chiller_asset_schema, build_water_pump_asset_schema
)
from climate_scenarios import apply_climate_scenario_transform, get_supported_climate_scenarios
from site_config import get_active_site_config
from schemas.requests import ScenarioAnalyzeRequest

router = APIRouter()


@router.get("/scenarios")
def scenarios_endpoint():
    return {"success": True, "scenarios": get_available_scenarios()}


def _do_scenario_analyze(location: str, scenario_name: str, tx_id: str) -> dict:
    """Shared logic for GET and POST /api/scenario-analyze."""
    # 1. Fetch live weather baseline
    weather_normalized = state.weather_client_inst.get_current_data(location)
    baseline_climate   = weather_normalized["data"]

    # 2. Apply what-if climate transformation
    climate_res = apply_climate_scenario_transform(baseline_climate, scenario_name)

    # 3. Retrieve asset data
    tx_sample   = get_live_data(tx_id)
    mod_v3_op   = tx_sample.get("data_v3", tx_sample.get("data", {}))
    mod_health  = tx_sample.get("health_data", {})
    _, health_rk = predict_health(mod_health)
    op_rk       = predict_operational(mod_v3_op)
    tx_contrib  = float(np.clip(health_rk * 0.40 + op_rk * 0.40 + baseline_climate.get("climate_stress", 19.7) * 0.20, 0, 100))
    tx_schema   = build_transformer_asset_schema(tx_contrib, health_rk, op_rk, risk_level(tx_contrib))

    # Chiller baseline
    chiller_sample_dict = {}
    if state.chiller_df is not None and len(state.chiller_df) > 0:
        s_idx = int(time.time() // 5) % len(state.chiller_df)
        chiller_sample_dict = state.chiller_df.iloc[s_idx].to_dict()

    chiller_risk = 5.0
    prob_normal  = 0.95
    pred_class   = 1
    prob_dict    = {f"Class_{i}": 0.05 for i in range(1, 9)}
    prob_dict["Class_1"] = 0.95
    chiller_level = "NORMAL"

    if state.chiller_model is not None and state.chiller_features:
        ch_vals = [float(chiller_sample_dict.get(feat, 0.0)) for feat in state.chiller_features]
        import pandas as pd
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

    ch_schema = build_chiller_asset_schema(chiller_risk, pred_class, prob_normal, prob_dict, chiller_level)

    # Water pump baseline
    pump_sample_dict = {}
    if state.water_pump_df is not None and len(state.water_pump_df) > 0:
        s_idx = int(time.time() // 5) % len(state.water_pump_df)
        pump_sample_dict = state.water_pump_df.iloc[s_idx].to_dict()

    pump_risk  = 15.0
    pred_state = "NORMAL"
    pump_level = "LOW"

    if state.water_pump_model is not None and state.water_pump_features:
        import pandas as pd
        p_vals = [float(pump_sample_dict.get(feat, 0.0)) for feat in state.water_pump_features]
        p_X = pd.DataFrame([p_vals], columns=state.water_pump_features)
        try:
            p_proba    = state.water_pump_model.predict_proba(p_X)[0]
            pump_risk  = round(float((p_proba[1]*0.33 + p_proba[2]*0.66 + p_proba[3]*1.00) * 100.0), 2)
            state_idx  = int(np.argmax(p_proba))
            state_map  = {0: "NORMAL", 1: "WATCH", 2: "WARNING", 3: "CRITICAL"}
            pred_state = state_map.get(state_idx, "NORMAL")
        except Exception:
            pump_risk = 20.0

    wp_schema = build_water_pump_asset_schema(pump_risk, pred_state, pump_level)

    # 4. Evaluate cascade what-if
    scenario_eval = evaluate_cascade_scenario(tx_schema, ch_schema, wp_schema, climate_res)

    return {
        "success": True,
        "scenario": {
            "name": climate_res["scenario_name"],
            "label": climate_res["label"],
            "description": climate_res["description"],
            "icon": climate_res["icon"],
            "simulated": climate_res["is_simulated"]
        },
        "weather": {
            "baseline": climate_res["baseline"],
            "scenario": climate_res["scenario"],
            "stress_change": climate_res["stress_change"]
        },
        "assets": scenario_eval["assets"],
        "cascade": {
            "baseline_risk": scenario_eval["baseline_risk"],
            "scenario_risk": scenario_eval["scenario_risk"],
            "change": scenario_eval["change"],
            "level": scenario_eval["level"]
        },
        "cascade_path": scenario_eval["cascade_path"],
        "path_notice": scenario_eval["path_notice"],
        "recommendation": scenario_eval["recommendation"]
    }


@router.get("/scenario-analyze")
def scenario_analyze_get(
    scenario: str = Query("HEATWAVE"),
    location: str = Query("Coimbatore"),
    tx_id: str = Query("TX-001")
):
    try:
        return _do_scenario_analyze(location, scenario, tx_id)
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scenario-analyze")
def scenario_analyze_post(body: ScenarioAnalyzeRequest):
    try:
        return _do_scenario_analyze(body.location, body.scenario, body.tx_id)
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scenario-summary")
def scenario_summary_endpoint(
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

        all_scenarios = get_supported_climate_scenarios()
        summary_list  = []

        w_norm = state.weather_client_inst.get_current_data(location=location, latitude=latitude, longitude=longitude)
        b_clim = w_norm["data"]

        tx_sample = get_live_data(tx_id)
        mod_v3_op = tx_sample.get("data_v3", tx_sample.get("data", {}))
        mod_health = tx_sample.get("health_data", {})
        _, health_rk = predict_health(mod_health)
        op_rk = predict_operational(mod_v3_op)
        tx_contrib = round(health_rk * 0.40 + op_rk * 0.40 + b_clim.get("climate_stress", 19.7) * 0.20, 2)
        tx_schema  = build_transformer_asset_schema(tx_contrib, health_rk, op_rk, risk_level(tx_contrib))
        ch_schema  = build_chiller_asset_schema(22.4, 1, 0.95, {}, "NORMAL")
        wp_schema  = build_water_pump_asset_schema(20.0, "NORMAL", "LOW")

        for sc_meta in all_scenarios:
            sc_name  = sc_meta["name"]
            clim_res = apply_climate_scenario_transform(b_clim, sc_name)
            eval_res = evaluate_cascade_scenario(tx_schema, ch_schema, wp_schema, clim_res)
            summary_list.append({
                "scenario": sc_name,
                "label": sc_meta["label"],
                "icon": sc_meta["icon"],
                "climate_stress": clim_res["scenario"]["climate_stress"],
                "transformer_risk": eval_res["assets"]["transformer"]["risk"],
                "chiller_risk": eval_res["assets"]["chiller"]["risk"],
                "pump_risk": eval_res["assets"]["water_pump"]["risk"],
                "system_risk": eval_res["scenario_risk"],
                "change": eval_res["change"]
            })

        return {
            "success": True,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "site": site_cfg,
            "location": location,
            "scenarios": summary_list
        }
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

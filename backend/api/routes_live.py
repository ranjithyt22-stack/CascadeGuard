"""
backend/api/routes_live.py
==========================
Transformer fleet, live-data, analyze, simulate-scenario endpoints.
Preserves all Phase 6 fleet analysis + Phase 7/8 backwards compat routes.
"""
import json
import time
import io

import numpy as np
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

import state
from state import (
    analyze_single_transformer, analyze_and_rank_fleet,
    predict_health, predict_operational, get_climate,
    risk_level, get_recommendation, get_model_signal,
    calculate_early_warning_state, get_dynamic_shap_explanation
)
from live_data import (
    get_live_data, reset_replay, get_replay_status, get_risk_history,
    get_transformers, get_fleet_samples, reset_fleet,
    push_fleet_history, get_fleet_history
)
from predictive_forecast import get_predictive_forecast
from decision_support import generate_decision_support
from scenarios import get_available_scenarios, apply_scenario
from schemas.requests import SimulateScenarioRequest, AnalyzeRequest

router = APIRouter()


# ── Transformer fleet ─────────────────────────────────────────────────────────

@router.get("/dashboard")
def dashboard_endpoint(
    site_id: str = Query(None),
    tx_id: str = Query("TX-001"),
    scenario: str = Query(None)
):
    try:
        active_sc = scenario or state.telemetry_mgr.active_scenario or "NORMAL"
        site = site_id or "CBE-001"
        
        site_res = state.analyze_site_internal(site, active_sc)
        
        tx_sample = get_live_data(tx_id)
        res_tx = analyze_single_transformer(tx_sample) if tx_sample.get("success") else {}
        
        climate = site_res.get("climate", {})
        temp = float(climate.get("temperature", 39.0))
        humidity = float(climate.get("humidity", 78.0))
        rain = float(climate.get("rain", 0.0))
        wind = float(climate.get("wind_speed", 18.0))
        c_stress = float(climate.get("climate_stress", 40.0))
        
        # Automatic Climate Stress Engine: evaluate directly from live weather parameters (Section 4 & 5)
        if temp >= 38.0:
            stress_level = "EXTREME HEAT"
            narrative = f"Current live ambient temperature ({temp}°C) generates severe thermal load on facility assets."
        elif temp >= 33.0:
            stress_level = "ELEVATED HEAT"
            narrative = f"Elevated ambient temperature ({temp}°C) increases cooling load and thermal dissipation demand."
        elif rain >= 15.0:
            stress_level = "HEAVY RAIN"
            narrative = f"Heavy rainfall ({rain} mm) increases water accumulation and moisture exposure risk."
        elif rain >= 5.0:
            stress_level = "RAINFALL STRESS"
            narrative = f"Active precipitation ({rain} mm) monitored across facility drainage sumps."
        elif c_stress > 40.0:
            stress_level = "ELEVATED STRESS"
            narrative = f"Combined environmental factors (Temp: {temp}°C, Humidity: {humidity}%, Wind: {wind} km/h) create elevated operating stress."
        else:
            stress_level = "NORMAL"
            narrative = f"Live weather parameters (Temp: {temp}°C, Humidity: {humidity}%, Rain: {rain} mm) are within normal operating bounds."
            
        assets_res = site_res.get("assets", {})
        tx_info = assets_res.get("transformer", {})
        ch_info = assets_res.get("chiller", {})
        wp_info = assets_res.get("water_pump", {})
        
        tx_score = round(float(tx_info.get("risk_score", tx_info.get("cascade_risk", 75.0))), 1)
        ch_score = round(float(ch_info.get("risk_score", ch_info.get("chiller_risk", 61.0))), 1)
        wp_score = round(float(wp_info.get("risk_score", wp_info.get("pump_risk", 27.0))), 1)
        
        tx_level = state.risk_level(tx_score)
        ch_level = state.risk_level(ch_score)
        wp_level = state.risk_level(wp_score)
        
        assets_normalized = {
            "transformer": {
                "asset_id": tx_id,
                "asset_name": "Power Transformer T01",
                "asset_type": "transformer",
                "risk_score": tx_score,
                "risk_level": tx_level,
                "metrics": {
                    "ambient_temp": temp,
                    "oil_temp": round(temp + 32.0, 1),
                    "winding_temp": round(temp + 44.0, 1),
                    "load_kw": 128.5,
                    "voltage_v": 230.4
                },
                "potential_impacts": ["Electrical Supply Line", "Chiller C01", "Hospital Core Cooling"]
            },
            "chiller": {
                "asset_id": "CH-001",
                "asset_name": "HVAC Chiller C01",
                "asset_type": "chiller",
                "risk_score": ch_score,
                "risk_level": ch_level,
                "metrics": {
                    "cooling_load_pct": round(min(100.0, temp * 2.1), 1),
                    "chilled_water_temp_c": 7.2,
                    "condenser_temp_c": round(temp + 8.5, 1),
                    "cop": 3.4
                },
                "potential_impacts": ["Hospital Cooling", "Medical Equipment Chillers"]
            },
            "water_pump": {
                "asset_id": "WP-001",
                "asset_name": "Industrial Water Pump P01",
                "asset_type": "water_pump",
                "risk_score": wp_score,
                "risk_level": wp_level,
                "metrics": {
                    "flow_rate_m3h": 142.0,
                    "discharge_bar": 4.1,
                    "motor_temp_c": round(temp + 12.0, 1),
                    "vibration_mms": 1.25
                },
                "potential_impacts": ["Basement Drainage Sump", "Cooling Tower Circulation"]
            }
        }
        
        asset_list = [
            {"asset_id": tx_id, "asset_type": "transformer", "asset_name": "Power Transformer T01", "risk_score": tx_score, "risk_level": tx_level},
            {"asset_id": "CH-001", "asset_type": "chiller", "asset_name": "HVAC Chiller C01", "risk_score": ch_score, "risk_level": ch_level},
            {"asset_id": "WP-001", "asset_type": "water_pump", "asset_name": "Water Pump P01", "risk_score": wp_score, "risk_level": wp_level}
        ]
        highest_risk = max(asset_list, key=lambda x: x["risk_score"])
        
        shap_factors, summary_text = state.get_dynamic_shap_explanation(tx_sample.get("data_v3", {})) if tx_sample.get("success") else ([], "SHAP unavailable")
        
        cascade_chain = [
            {"step": 1, "node": f"{highest_risk['asset_name']}", "type": "Primary Asset", "status": "VULNERABLE"},
            {"step": 2, "node": "Electrical & Control Bus", "type": "Substation Infrastructure", "status": "AT RISK"},
            {"step": 3, "node": "HVAC Chiller C01", "type": "Cooling System", "status": "POTENTIAL IMPACT"},
            {"step": 4, "node": "Hospital Core Services", "type": "Downstream Facility", "status": "INSPECT NOW"}
        ]
        
        mults = {"NOW": 1.0, "+24H": 0.95, "+48H": 1.08, "+72H": 1.15}
        forecast_72h = {
            "label": "PROJECTED RISK",
            "timeline": ["NOW", "+24H", "+48H", "+72H"],
            "transformer": [round(min(100.0, tx_score * m), 1) for m in mults.values()],
            "chiller": [round(min(100.0, ch_score * m), 1) for m in mults.values()],
            "water_pump": [round(min(100.0, wp_score * m), 1) for m in mults.values()]
        }
        
        rec_list = site_res.get("recommendation", [])
        if isinstance(rec_list, str):
            rec_list = [rec_list]
        if not rec_list:
            rec_list = [
                f"Inspect {highest_risk['asset_name']} cooling radiator and verify fan operation.",
                f"Review electrical load distribution for {highest_risk['asset_name']}.",
                "Schedule thermal imaging assessment during peak ambient heat."
            ]
        top_actions = rec_list[:3]
        
        return {
            "success": True,
            "facility": {
                "site_id": site_res.get("site", {}).get("site_id", "SITE-001"),
                "site_name": site_res.get("site", {}).get("site_name", "Coimbatore Regional Infrastructure Hub"),
                "city": site_res.get("location", "Coimbatore"),
                "region": "Tamil Nadu, India",
                "latitude": site_res.get("site", {}).get("latitude", 11.0168),
                "longitude": site_res.get("site", {}).get("longitude", 76.9558)
            },
            "data_provenance": {
                "weather": "LIVE",
                "transformer_telemetry": "REPLAY",
                "chiller_telemetry": "REPLAY",
                "water_pump_telemetry": "REPLAY"
            },
            "weather": {
                "temperature": temp,
                "humidity": humidity,
                "rain": rain,
                "wind_speed": wind,
                "condition": "LIVE OPEN-METEO DATA"
            },
            "climate_stress": {
                "score": c_stress,
                "level": stress_level,
                "narrative": narrative
            },
            "assets": assets_normalized,
            "highest_risk_asset": highest_risk,
            "shap": {
                "asset_id": highest_risk["asset_id"],
                "asset_name": highest_risk["asset_name"],
                "factors": shap_factors[:5],
                "summary": summary_text,
                "explanation_available": len(shap_factors) > 0
            },
            "cascade": {
                "primary_asset": highest_risk["asset_name"],
                "chain": cascade_chain,
                "description": f"Vulnerability in {highest_risk['asset_name']} may propagate stress downstream to cooling and facility services."
            },
            "forecast_72h": forecast_72h,
            "recommendations": top_actions,
            "active_scenario": active_sc
        }
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transformers")
def transformers_endpoint():
    return {"success": True, "transformers": get_transformers()}


@router.get("/fleet-status")
def fleet_status_endpoint():
    try:
        fleet_list, fleet_summary = analyze_and_rank_fleet()
        return {"success": True, "summary": fleet_summary, "transformers": fleet_list}
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fleet-analyze")
def fleet_analyze_endpoint():
    fleet_list, fleet_summary = analyze_and_rank_fleet()
    return {"success": True, "summary": fleet_summary, "transformers": fleet_list}


@router.get("/transformer/{tx_id}")
def single_transformer_endpoint(tx_id: str):
    sample = get_live_data(tx_id)
    if not sample.get("success"):
        raise HTTPException(status_code=404, detail=sample.get("error", "Transformer not found"))
    return analyze_single_transformer(sample)


@router.get("/fleet-history")
def fleet_history_endpoint():
    return {"success": True, "history": get_fleet_history()}


@router.post("/fleet/reset")
def fleet_reset_endpoint():
    state.predictive_history.clear()
    return reset_fleet()


# ── Live data (backwards compat) ─────────────────────────────────────────────

@router.get("/live-data")
def live_data_sample(tx_id: str = Query("TX-001")):
    return get_live_data(tx_id)


@router.post("/live-data/reset")
def live_data_reset():
    state.predictive_history.clear()
    return reset_replay()


@router.get("/live-data/status")
def live_data_status(tx_id: str = Query("TX-001")):
    return get_replay_status(tx_id)


@router.get("/risk-history")
def risk_history_endpoint(tx_id: str = Query("TX-001")):
    return {"success": True, "history": get_risk_history(tx_id)}


@router.get("/predictive-history")
def predictive_history_endpoint():
    return {"success": True, "history": list(state.predictive_history)}


# ── Predictive forecast ───────────────────────────────────────────────────────

@router.get("/predictive-forecast")
def predictive_forecast_endpoint(tx_id: str = Query("TX-001")):
    try:
        sample = get_live_data(tx_id)
        if not sample.get("success"):
            raise HTTPException(status_code=500, detail=sample.get("error"))
        res = analyze_single_transformer(sample)
        history_rec = {
            "timestamp": sample["timestamp"],
            "current_score": res["cascade"]["score"],
            "cas_15m": res["predictive_forecast"]["forecast"]["15m"]["cascade_score"],
            "cas_30m": res["predictive_forecast"]["forecast"]["30m"]["cascade_score"],
            "cas_60m": res["predictive_forecast"]["forecast"]["60m"]["cascade_score"],
            "prob_60m": res["predictive_forecast"]["forecast"]["60m"]["event_probability"],
            "early_warning": res["explainability"]["early_warning_state"]
        }
        state.predictive_history.append(history_rec)
        return {
            "success": True,
            "source": "historical_replay",
            "mode": "predictive_simulation",
            "transformer_id": tx_id,
            "timestamp": sample["timestamp"],
            "predictive_forecast": res["predictive_forecast"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Export report ─────────────────────────────────────────────────────────────

@router.get("/export-report")
def export_report_endpoint(tx_id: str = Query("TX-001"), download: str = Query("false")):
    sample = get_live_data(tx_id)
    res = analyze_single_transformer(sample)

    report_data = {
        "system": "CascadeGuard AI Command Center",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "transformer_id": tx_id,
        "display_name": res["display_name"],
        "location": res["location"],
        "data_provenance": res["data_provenance"],
        "metrics": {
            "health_index": res["health"]["index"],
            "health_risk": res["health"]["risk"],
            "operational_risk": res["operational"]["risk"],
            "climate_stress": res["climate"]["climate_stress"],
            "cascade_score": res["cascade"]["score"],
            "risk_level": res["cascade"]["level"],
            "early_warning_state": res["explainability"]["early_warning_state"],
            "risk_trend": res["explainability"]["trend"]
        },
        "top_shap_factors": res["explainability"]["top_factors"],
        "decision_support": res["decision_support"],
        "recommendation": res["recommendation"]
    }

    if download.lower() == "true":
        content = json.dumps(report_data, indent=2)
        from fastapi.responses import Response
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment;filename=CascadeGuard_{tx_id}_Risk_Report.json"}
        )

    return {"success": True, "report": report_data}


# ── Live analyze (backwards compat) ──────────────────────────────────────────

@router.get("/live-analyze")
def live_analyze(tx_id: str = Query("TX-001")):
    try:
        sample = get_live_data(tx_id)
        if not sample.get("success"):
            raise HTTPException(status_code=500, detail=sample.get("error"))
        return analyze_single_transformer(sample)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /api/analyze (backwards compat) ─────────────────────────────────────

@router.post("/analyze")
def analyze(body: AnalyzeRequest):
    try:
        data = body.model_dump()
        location = data.pop("location", "Coimbatore")

        health_index, health_risk = predict_health(data)
        operational_risk = predict_operational(data)
        climate = get_climate(location)

        health_contrib  = round(health_risk * 0.40, 2)
        op_contrib      = round(operational_risk * 0.40, 2)
        climate_contrib = round(climate["climate_stress"] * 0.20, 2)

        final_risk       = float(np.clip(health_contrib + op_contrib + climate_contrib, 0, 100))
        final_risk_round = round(final_risk, 2)
        level            = risk_level(final_risk_round)
        recommendation   = get_recommendation(level)

        top_factors, summary_text = get_dynamic_shap_explanation(data)

        return {
            "success": True,
            "operational_model_version": state.operational_model_version,
            "health": {"index": round(health_index, 2), "risk": round(health_risk, 2)},
            "operational": {"risk": round(operational_risk, 2)},
            "climate": climate,
            "cascade": {"score": final_risk_round, "level": level},
            "cascade_breakdown": {
                "health_risk": round(health_risk, 2),
                "operational_risk": round(operational_risk, 2),
                "climate_stress": climate["climate_stress"],
                "health_weight": 0.40,
                "operational_weight": 0.40,
                "climate_weight": 0.20,
                "health_contribution": health_contrib,
                "operational_contribution": op_contrib,
                "climate_contribution": climate_contrib,
                "final_score": final_risk_round
            },
            "explainability": {
                "top_factors": top_factors,
                "summary": summary_text,
                "trend": "STABLE",
                "trend_change": 0.0,
                "early_warning_state": calculate_early_warning_state(final_risk_round, "STABLE", operational_risk),
                "model_signal": get_model_signal(operational_risk)
            },
            "recommendation": recommendation
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /api/simulate-scenario ───────────────────────────────────────────────

@router.post("/simulate-scenario")
def simulate_scenario(body: SimulateScenarioRequest):
    try:
        scenario_name = body.scenario
        tx_id         = body.tx_id
        location      = body.location

        sample = get_live_data(tx_id)
        if not sample.get("success"):
            raise HTTPException(status_code=500, detail=sample.get("error"))

        base_op_raw = sample["data"]
        base_op_v3  = sample.get("data_v3", base_op_raw)
        base_health = sample["health_data"]
        base_climate = get_climate(location)

        b_h_idx, b_h_rk = predict_health(base_health)
        b_op_rk = predict_operational(base_op_v3)
        b_score  = float(np.clip(b_h_rk * 0.40 + b_op_rk * 0.40 + base_climate["climate_stress"] * 0.20, 0, 100))
        b_score_round = round(b_score, 2)

        mod_op_raw, mod_op_v3, mod_health, mod_climate, deltas, meta = apply_scenario(
            scenario_name, base_op_raw, base_op_v3, base_health, base_climate
        )

        s_h_idx, s_h_rk = predict_health(mod_health)
        s_op_rk = predict_operational(mod_op_v3)
        s_score  = float(np.clip(s_h_rk * 0.40 + s_op_rk * 0.40 + mod_climate["climate_stress"] * 0.20, 0, 100))
        s_score_round = round(s_score, 2)

        s_level  = risk_level(s_score_round)
        b_level  = risk_level(b_score_round)
        risk_change = round(s_score_round - b_score_round, 2)
        direction   = "INCREASED" if risk_change > 0 else ("DECREASED" if risk_change < 0 else "UNCHANGED")

        tx_sample_sim = {
            "transformer_id": tx_id,
            "display_name": f"{sample['display_name']} ({meta['label']})",
            "location": location,
            "timestamp": f"{sample['timestamp']} [{scenario_name}]",
            "current_index": sample["current_index"],
            "data": mod_op_raw,
            "data_v3": mod_op_v3,
            "health_data": mod_health,
            "scenario": meta
        }

        res = analyze_single_transformer(tx_sample_sim)
        res["source"] = "simulated_scenario"
        res["comparison"] = {
            "baseline_score": b_score_round,
            "baseline_level": b_level,
            "scenario_score": s_score_round,
            "scenario_level": s_level,
            "change": risk_change,
            "direction": direction
        }
        res["scenario_impact"] = deltas
        return res

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

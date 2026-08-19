import sys
import os
import io
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from flask import Flask, request, jsonify, Response, send_file
from pathlib import Path
import json
import time
from collections import deque

import pandas as pd
import numpy as np
import joblib
import requests
import shap

from live_data import (
    get_live_data, reset_replay, get_replay_status, push_risk_history, get_risk_history,
    get_transformers, get_fleet_samples, reset_fleet, push_fleet_history, get_fleet_history
)
from scenarios import get_available_scenarios, apply_scenario
from decision_support import generate_decision_support
from predictive_forecast import get_predictive_forecast
from cascade_graph import (
    evaluate_cascade_graph, evaluate_cascade_scenario, build_transformer_asset_schema,
    build_chiller_asset_schema, build_water_pump_asset_schema
)
from api_clients import (
    WeatherAPIClient, TransformerTelemetryClient, ChillerTelemetryClient, WaterPumpTelemetryClient
)
from climate_scenarios import (
    apply_climate_scenario_transform, get_supported_climate_scenarios
)
from site_config import (
    validate_site_config, get_active_site_config, set_active_site_config
)
from climate_intelligence import analyze_climate_intelligence
from ot.telemetry_manager import TelemetryManager
from incident_engine import IncidentEngine
from alert_manager import AlertManager
from report_generator import generate_pdf_report
from site_registry import SiteRegistry, validate_coordinates
from regional_risk_engine import RegionalRiskEngine

app = Flask(__name__)

site_registry = SiteRegistry()
regional_risk_engine = RegionalRiskEngine()

weather_client_inst = WeatherAPIClient()
transformer_client_inst = TransformerTelemetryClient()
chiller_client_inst = ChillerTelemetryClient()
water_pump_client_inst = WaterPumpTelemetryClient()

# Basic CORS headers helper
@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
    return response


# ============================================================
# PATH RESOLUTION & LOAD MODELS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

HEALTH_MODEL_PATH = BASE_DIR / "models" / "health_index_xgboost.pkl"
OPERATIONAL_MODEL_V3_PATH = BASE_DIR / "models" / "operational_stress_xgboost_v3.pkl"
OPERATIONAL_MODEL_V2_PATH = BASE_DIR / "models" / "operational_stress_xgboost_v2.pkl"
OPERATIONAL_FEATURES_V3_PATH = BASE_DIR / "models" / "operational_features_v3.csv"
METADATA_PATH = BASE_DIR / "models" / "operational_model_metadata.json"

health_model = joblib.load(HEALTH_MODEL_PATH)

# Load Operational Model V3 (or fallback to V2)
if OPERATIONAL_MODEL_V3_PATH.exists():
    operational_model = joblib.load(OPERATIONAL_MODEL_V3_PATH)
    operational_model_version = "v3"
else:
    operational_model = joblib.load(OPERATIONAL_MODEL_V2_PATH)
    operational_model_version = "v2"

# Load Features V3 list
OPERATIONAL_FEATURES_V3 = []
if OPERATIONAL_FEATURES_V3_PATH.exists():
    with open(OPERATIONAL_FEATURES_V3_PATH, "r") as f:
        OPERATIONAL_FEATURES_V3 = [line.strip() for line in f if line.strip()]

# Load Metadata
operational_metadata = {}
if METADATA_PATH.exists():
    try:
        with open(METADATA_PATH, "r") as f:
            operational_metadata = json.load(f)
    except Exception:
        pass

# Load Chiller Model & Metadata (Phase 9)
CHILLER_MODEL_PATH = BASE_DIR / "models" / "chiller_xgboost.pkl"
CHILLER_FEATURES_PATH = BASE_DIR / "models" / "chiller_features.csv"
CHILLER_MAPPING_PATH = BASE_DIR / "models" / "chiller_label_mapping.json"
CHILLER_DATA_PATH = BASE_DIR / "data" / "raw" / "chiller" / "11000.xlsx"

chiller_model = joblib.load(CHILLER_MODEL_PATH) if CHILLER_MODEL_PATH.exists() else None
chiller_features = []
if CHILLER_FEATURES_PATH.exists():
    with open(CHILLER_FEATURES_PATH) as f:
        chiller_features = [l.strip() for l in f if l.strip()]

chiller_mapping = {}
if CHILLER_MAPPING_PATH.exists():
    with open(CHILLER_MAPPING_PATH) as f:
        chiller_mapping = json.load(f)

chiller_df = None
if CHILLER_DATA_PATH.exists():
    try:
        chiller_df = pd.read_excel(CHILLER_DATA_PATH, sheet_name="Sheet1")
    except Exception as e:
        print("Chiller data load note:", e)

# Load Water Pump Model & Decision Metadata (Phase 9)
WATER_PUMP_MODEL_PATH = BASE_DIR / "models" / "water_pump_xgboost.pkl"
WATER_PUMP_FEATURES_PATH = BASE_DIR / "models" / "water_pump_features.csv"
WATER_PUMP_DECISION_PATH = BASE_DIR / "models" / "water_pump_model_decision.json"
WATER_PUMP_DATA_PATH = BASE_DIR / "data" / "raw" / "water_pump" / "rul_hrs.csv"

water_pump_model = joblib.load(WATER_PUMP_MODEL_PATH) if WATER_PUMP_MODEL_PATH.exists() else None
water_pump_features = []
if WATER_PUMP_FEATURES_PATH.exists():
    with open(WATER_PUMP_FEATURES_PATH) as f:
        water_pump_features = [l.strip() for l in f if l.strip()]

water_pump_decision = {}
if WATER_PUMP_DECISION_PATH.exists():
    with open(WATER_PUMP_DECISION_PATH) as f:
        water_pump_decision = json.load(f)

water_pump_df = None
if WATER_PUMP_DATA_PATH.exists():
    try:
        water_pump_df = pd.read_csv(WATER_PUMP_DATA_PATH)
    except Exception as e:
        print("Water Pump data load note:", e)

# Instantiate SHAP TreeExplainer globally for instant <10ms evaluation
shap_explainer = None
if operational_model is not None:
    try:
        shap_explainer = shap.TreeExplainer(operational_model)
    except Exception as e:
        print("SHAP explainer init note:", e)

# Deque for predictive forecast history
predictive_history = deque(maxlen=50)


# ============================================================
# FEATURE MAPPINGS & DYNAMIC EXPLAINABILITY
# ============================================================

HEALTH_FEATURES = [
    "Hydrogen", "Oxigen", "Nitrogen", "Methane", "CO", "CO2",
    "Ethylene", "Ethane", "Acethylene", "DBDS",
    "Power factor", "Interfacial V", "Dielectric rigidity", "Water content"
]

OPERATIONAL_FEATURES_RAW = [
    "ATI", "OTI", "WTI", "OLI",
    "VL1", "VL2", "VL3", "VL12", "VL23", "VL31",
    "IL1", "IL2", "IL3", "INUT",
    "WL1", "WL2", "WL3",
    "VAL1", "VAL2", "VAL3",
    "RVAL1", "RVAL2", "RVAL3",
    "PFL1", "PFL2", "PFL3",
    "Avg_PF", "Sum_PF",
    "FRQ",
    "THDVL1", "THDVL2", "THDVL3",
    "THDIL1", "THDIL2", "THDIL3",
    "KW", "KVA", "KVAR",
    "MPD", "MKVAD"
]

FEATURE_HUMAN_MAPPINGS = {
    "MPD_roll60m_mean": "High 60-minute average maximum power demand",
    "KW_roll30m_mean": "Elevated 30-minute active power load",
    "THDVL1_roll60m_mean": "Elevated 60-minute voltage harmonic distortion (Phase L1)",
    "THDVL1_roll30m_mean": "Recent voltage harmonic distortion (Phase L1)",
    "OTI": "Instantaneous oil temperature index",
    "WTI": "Winding temperature index",
    "ATI": "Ambient temperature level",
    "OLI": "Transformer oil level indicator",
    "VL1": "Phase L1 line voltage",
    "VL23": "Phase L23 line-to-line voltage",
    "VL31": "Phase L31 line-to-line voltage",
    "IL1": "Phase L1 load current",
    "KW": "Instantaneous active power demand",
    "KVA": "Apparent power load",
    "Avg_PF": "Average power factor across phases",
    "FRQ": "Grid frequency stability",
    "MPD": "Instantaneous maximum power demand",
    "ATI_roll30m_mean": "Elevated recent ambient temperature",
    "OTI_roll30m_mean": "Sustained high oil temperature over the last 30 minutes",
    "OTI_roll60m_mean": "Persistent high oil temperature over the last hour",
    "OTI_diff1": "Rapid rate of oil temperature change"
}


def get_feature_description(feature):
    if feature in FEATURE_HUMAN_MAPPINGS:
        return FEATURE_HUMAN_MAPPINGS[feature]
    clean = feature.replace("_roll30m_mean", " (30m avg)").replace("_roll60m_mean", " (60m avg)").replace("_diff1", " rate of change")
    return f"{clean} operational telemetry level"


def get_dynamic_shap_explanation(data_v3):
    if shap_explainer is None or not OPERATIONAL_FEATURES_V3:
        return [], "SHAP explainer uninitialized."

    values = [float(data_v3.get(feat, 0.0)) for feat in OPERATIONAL_FEATURES_V3]
    X = pd.DataFrame([values], columns=OPERATIONAL_FEATURES_V3)

    try:
        raw_shap = shap_explainer(X).values[0]
    except Exception:
        raw_shap = np.zeros(len(OPERATIONAL_FEATURES_V3))

    factors = []
    for feat, val, s_val in zip(OPERATIONAL_FEATURES_V3, values, raw_shap):
        s_val_float = float(s_val)
        abs_s = abs(s_val_float)
        direction = "increases_risk" if s_val_float >= 0 else "decreases_risk"
        
        if abs_s >= 0.50:
            impact = "HIGH"
        elif abs_s >= 0.15:
            impact = "MEDIUM"
        else:
            impact = "LOW"

        factors.append({
            "feature": feat,
            "description": get_feature_description(feat),
            "value": round(val, 2),
            "shap_value": round(s_val_float, 4),
            "abs_shap": round(abs_s, 4),
            "direction": direction,
            "impact": impact
        })

    factors.sort(key=lambda x: x["abs_shap"], reverse=True)
    top_5 = factors[:5]

    inc_factors = [f["description"].lower() for f in top_5 if f["direction"] == "increases_risk"]
    if inc_factors:
        summary = f"Operational risk signal is influenced primarily by {inc_factors[0]}"
        if len(inc_factors) > 1:
            summary += f" and {inc_factors[1]}."
        else:
            summary += "."
    else:
        summary = "Operational conditions are stable with minimal predicted risk contributions."

    return top_5, summary


# ============================================================
# HELPER PREDICTION & TREND FUNCTIONS
# ============================================================

def predict_health(data):
    values = []
    for feature in HEALTH_FEATURES:
        values.append(float(data.get(feature, 0)))

    X = pd.DataFrame([values], columns=HEALTH_FEATURES)
    health_index = float(health_model.predict(X)[0])
    health_index = np.clip(health_index, 0, 100)
    health_risk = 100 - health_index
    return health_index, health_risk


def predict_operational(data):
    if operational_model_version == "v3" and OPERATIONAL_FEATURES_V3:
        feature_list = OPERATIONAL_FEATURES_V3
    else:
        feature_list = OPERATIONAL_FEATURES_RAW

    values = []
    for feature in feature_list:
        values.append(float(data.get(feature, 0)))

    X = pd.DataFrame([values], columns=feature_list)
    probability = float(operational_model.predict_proba(X)[0][1])
    return probability * 100


CLIMATE_CACHE = {}

def get_climate(location="Coimbatore", latitude=None, longitude=None):
    if latitude is None or longitude is None:
        site_cfg = get_active_site_config()
        if site_cfg and "location" in site_cfg:
            latitude = site_cfg["location"]["latitude"]
            longitude = site_cfg["location"]["longitude"]
            if not location or location == "Coimbatore":
                location = site_cfg["location"]["name"]

    normalized = weather_client_inst.get_current_data(location=location, latitude=latitude, longitude=longitude)
    return normalized["data"]


def risk_level(score):
    if score < 25:
        return "LOW"
    elif score < 50:
        return "MODERATE"
    elif score < 75:
        return "HIGH"
    return "CRITICAL"


def get_recommendation(level):
    if level == "LOW":
        return "Continue normal monitoring."
    elif level == "MODERATE":
        return "Increase monitoring frequency and inspect risk indicators."
    elif level == "HIGH":
        return "Prioritize transformer inspection and evaluate load/cooling conditions."
    return "Immediate engineering assessment and protective action recommended."


def get_model_signal(score):
    if score < 20:
        return "LOW"
    elif score < 50:
        return "MODERATE"
    elif score < 75:
        return "HIGH"
    return "CRITICAL"


def calculate_risk_trend(history):
    if not history or len(history) < 2:
        return "STABLE", 0.0

    scores = [h["cascade_score"] for h in history]
    if len(scores) < 4:
        diff = round(scores[-1] - scores[0], 2)
    else:
        recent = scores[-3:]
        older = scores[-6:-3]
        avg_recent = sum(recent) / len(recent)
        avg_older = sum(older) / len(older)
        diff = round(avg_recent - avg_older, 2)

    if diff > 2.0:
        trend = "RISING"
    elif diff < -2.0:
        trend = "FALLING"
    else:
        trend = "STABLE"

    return trend, diff


def calculate_early_warning_state(score, trend, op_risk):
    if score >= 75 or (score >= 60 and trend == "RISING"):
        return "CRITICAL"
    elif score >= 50 or (score >= 40 and trend == "RISING"):
        return "WARNING"
    elif score >= 25 or trend == "RISING":
        return "WATCH"
    return "NORMAL"


# ============================================================
# PHASE 6: FLEET ANALYSIS & RANKING ENGINE
# ============================================================

def analyze_single_transformer(tx_sample):
    tx_id = tx_sample["transformer_id"]
    location = tx_sample["location"]
    
    op_data_raw = tx_sample["data"]
    op_data_v3 = tx_sample.get("data_v3", op_data_raw)
    health_data = tx_sample["health_data"]

    health_idx, health_rk = predict_health(health_data)
    op_rk = predict_operational(op_data_v3)
    climate = get_climate(location)

    health_contrib = round(health_rk * 0.40, 2)
    op_contrib = round(op_rk * 0.40, 2)
    climate_contrib = round(climate["climate_stress"] * 0.20, 2)

    final_risk = float(np.clip(health_contrib + op_contrib + climate_contrib, 0, 100))
    final_risk_round = round(final_risk, 2)
    level = risk_level(final_risk_round)

    top_factors, summary_text = get_dynamic_shap_explanation(op_data_v3)

    history_record = {
        "timestamp": tx_sample["timestamp"],
        "operational_risk": round(op_rk, 2),
        "health_risk": round(health_rk, 2),
        "climate_stress": climate["climate_stress"],
        "cascade_score": final_risk_round,
        "level": level
    }
    push_fleet_history(tx_id, history_record)

    tx_history = get_risk_history(tx_id)
    trend, trend_change = calculate_risk_trend(tx_history)
    early_warning = calculate_early_warning_state(final_risk_round, trend, op_rk)
    model_signal = get_model_signal(op_rk)

    forecast_res = get_predictive_forecast(
        op_data_raw, op_data_v3, health_rk, climate["climate_stress"], final_risk_round
    )

    decision_support = generate_decision_support(
        final_risk_round, level, early_warning, trend, top_factors, climate, tx_sample.get("scenario", {}).get("name", "NORMAL")
    )

    # Priority score math for fleet ranking
    cas_60m = forecast_res["forecast"]["60m"]["cascade_score"]
    trend_w = 10.0 if trend == "RISING" else (0.0 if trend == "STABLE" else -5.0)
    ew_w = 15.0 if early_warning == "CRITICAL" else (10.0 if early_warning == "WARNING" else (5.0 if early_warning == "WATCH" else 0.0))
    priority_score = round(0.40 * final_risk_round + 0.40 * cas_60m + trend_w + ew_w, 2)

    return {
        "success": True,
        "transformer_id": tx_id,
        "display_name": tx_sample["display_name"],
        "location": location,
        "scenario": tx_sample.get("scenario", {}),
        "timestamp": tx_sample["timestamp"],
        "current_index": tx_sample["current_index"],
        "data_provenance": {
            "telemetry": "HISTORICAL TELEMETRY REPLAY",
            "weather": "LIVE OPEN-METEO API",
            "model_version": operational_model_version
        },
        "health": {
            "index": round(health_idx, 2),
            "risk": round(health_rk, 2)
        },
        "operational": {
            "risk": round(op_rk, 2)
        },
        "climate": climate,
        "cascade": {
            "score": final_risk_round,
            "level": level
        },
        "cascade_breakdown": {
            "health_risk": round(health_rk, 2),
            "operational_risk": round(op_rk, 2),
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
            "trend": trend,
            "trend_change": trend_change,
            "early_warning_state": early_warning,
            "model_signal": model_signal
        },
        "predictive_forecast": forecast_res,
        "decision_support": decision_support,
        "recommendation": decision_support["summary"],
        "priority_score": priority_score,
        "telemetry": op_data_raw
    }


def analyze_and_rank_fleet():
    fleet_samples = get_fleet_samples()
    analyzed_list = []

    for tx_id, sample in fleet_samples.items():
        if sample.get("success"):
            tx_res = analyze_single_transformer(sample)
            analyzed_list.append(tx_res)

    # Rank by Priority Score descending
    analyzed_list.sort(key=lambda x: x["priority_score"], reverse=True)

    # Assign priority rank (1 to N)
    normal_c, watch_c, warning_c, critical_c, rising_c = 0, 0, 0, 0, 0
    total_score = 0.0

    for idx, tx in enumerate(analyzed_list):
        tx["priority_rank"] = idx + 1
        level = tx["cascade"]["level"]
        ew = tx["explainability"]["early_warning_state"]
        tr = tx["explainability"]["trend"]

        total_score += tx["cascade"]["score"]
        if ew == "CRITICAL" or level == "CRITICAL": critical_c += 1
        elif ew == "WARNING" or level == "HIGH": warning_c += 1
        elif ew == "WATCH" or level == "MODERATE": watch_c += 1
        else: normal_c += 1

        if tr == "RISING": rising_c += 1

    n_tx = max(len(analyzed_list), 1)
    fleet_risk = round(total_score / n_tx, 2)
    top_tx = analyzed_list[0] if analyzed_list else None

    highest_risk_info = {
        "transformer_id": top_tx["transformer_id"] if top_tx else "N/A",
        "display_name": top_tx["display_name"] if top_tx else "N/A",
        "score": top_tx["cascade"]["score"] if top_tx else 0.0,
        "level": top_tx["cascade"]["level"] if top_tx else "LOW",
        "forecast_60m": top_tx["predictive_forecast"]["forecast"]["60m"]["cascade_score"] if top_tx else 0.0
    }

    fleet_summary = {
        "total_monitored": len(analyzed_list),
        "fleet_risk": fleet_risk,
        "fleet_status": risk_level(fleet_risk),
        "highest_risk_transformer": highest_risk_info,
        "normal_count": normal_c,
        "watch_count": watch_c,
        "warning_count": warning_c,
        "critical_count": critical_c,
        "rising_risk_count": rising_c
    }

    return analyzed_list, fleet_summary


# ============================================================
# API ENDPOINTS
# ============================================================

@app.route("/api/health")
def health():
    return jsonify({
        "status": "online",
        "service": "CascadeGuard AI Command Center",
        "operational_model_version": operational_model_version,
        "shap_explainer": "active" if shap_explainer is not None else "inactive",
        "scenarios_available": 8,
        "predictive_forecasting": "active",
        "transformers_monitored": len(get_transformers())
    })


@app.route("/api/transformers", methods=["GET"])
def transformers_endpoint():
    return jsonify({
        "success": True,
        "transformers": get_transformers()
    })


@app.route("/api/fleet-status", methods=["GET"])
def fleet_status_endpoint():
    try:
        fleet_list, fleet_summary = analyze_and_rank_fleet()
        return jsonify({
            "success": True,
            "summary": fleet_summary,
            "transformers": fleet_list
        })
    except Exception as e:
        import traceback
        print("ERROR IN FLEET STATUS ENDPOINT:", e)
        traceback.print_exc()
        sys.stdout.flush()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/fleet-analyze", methods=["GET"])
def fleet_analyze_endpoint():
    fleet_list, fleet_summary = analyze_and_rank_fleet()
    return jsonify({
        "success": True,
        "summary": fleet_summary,
        "transformers": fleet_list
    })


@app.route("/api/transformer/<tx_id>", methods=["GET"])
def single_transformer_endpoint(tx_id):
    sample = get_live_data(tx_id)
    if not sample.get("success"):
        return jsonify(sample), 404

    res = analyze_single_transformer(sample)
    return jsonify(res)


@app.route("/api/fleet-history", methods=["GET"])
def fleet_history_endpoint():
    return jsonify({
        "success": True,
        "history": get_fleet_history()
    })


@app.route("/api/fleet/reset", methods=["POST"])
def fleet_reset_endpoint():
    predictive_history.clear()
    res = reset_fleet()
    return jsonify(res)


@app.route("/api/live-data", methods=["GET"])
def live_data_sample():
    tx_id = request.args.get("tx_id", "TX-001")
    sample = get_live_data(tx_id)
    return jsonify(sample)


@app.route("/api/live-data/reset", methods=["POST"])
def live_data_reset():
    predictive_history.clear()
    result = reset_replay()
    return jsonify(result)


@app.route("/api/live-data/status", methods=["GET"])
def live_data_status():
    tx_id = request.args.get("tx_id", "TX-001")
    status = get_replay_status(tx_id)
    return jsonify(status)


@app.route("/api/risk-history", methods=["GET"])
def risk_history_endpoint():
    tx_id = request.args.get("tx_id", "TX-001")
    history = get_risk_history(tx_id)
    return jsonify({
        "success": True,
        "history": history
    })


@app.route("/api/predictive-history", methods=["GET"])
def predictive_history_endpoint():
    return jsonify({
        "success": True,
        "history": list(predictive_history)
    })


@app.route("/api/scenarios", methods=["GET"])
def scenarios_endpoint():
    return jsonify({
        "success": True,
        "scenarios": get_available_scenarios()
    })


@app.route("/api/predictive-forecast", methods=["GET"])
def predictive_forecast_endpoint():
    try:
        tx_id = request.args.get("tx_id", "TX-001")
        sample = get_live_data(tx_id)
        if not sample.get("success"):
            return jsonify(sample), 500

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
        predictive_history.append(history_rec)

        return jsonify({
            "success": True,
            "source": "historical_replay",
            "mode": "predictive_simulation",
            "transformer_id": tx_id,
            "timestamp": sample["timestamp"],
            "predictive_forecast": res["predictive_forecast"]
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/export-report", methods=["GET"])
def export_report_endpoint():
    tx_id = request.args.get("tx_id", "TX-001")
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

    if request.args.get("download") == "true":
        return Response(
            json.dumps(report_data, indent=2),
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment;filename=CascadeGuard_{tx_id}_Risk_Report.json"}
        )

    return jsonify({"success": True, "report": report_data})


@app.route("/api/live-analyze", methods=["GET"])
def live_analyze():
    try:
        tx_id = request.args.get("tx_id", "TX-001")
        sample = get_live_data(tx_id)
        if not sample.get("success"):
            return jsonify(sample), 500

        res = analyze_single_transformer(sample)
        return jsonify(res)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/simulate-scenario", methods=["POST"])
def simulate_scenario():
    start_t = time.time()
    try:
        req_data = request.get_json() or {}
        scenario_name = req_data.get("scenario", "NORMAL")
        tx_id = req_data.get("tx_id", "TX-001")
        location = req_data.get("location", "Coimbatore")

        sample = get_live_data(tx_id)
        if not sample.get("success"):
            return jsonify(sample), 500

        base_op_raw = sample["data"]
        base_op_v3 = sample.get("data_v3", base_op_raw)
        base_health = sample["health_data"]

        base_climate = get_climate(location)

        b_h_idx, b_h_rk = predict_health(base_health)
        b_op_rk = predict_operational(base_op_v3)
        b_score = float(np.clip(b_h_rk * 0.40 + b_op_rk * 0.40 + base_climate["climate_stress"] * 0.20, 0, 100))
        b_score_round = round(b_score, 2)

        mod_op_raw, mod_op_v3, mod_health, mod_climate, deltas, meta = apply_scenario(
            scenario_name, base_op_raw, base_op_v3, base_health, base_climate
        )

        s_h_idx, s_h_rk = predict_health(mod_health)
        s_op_rk = predict_operational(mod_op_v3)
        s_score = float(np.clip(s_h_rk * 0.40 + s_op_rk * 0.40 + mod_climate["climate_stress"] * 0.20, 0, 100))
        s_score_round = round(s_score, 2)

        s_level = risk_level(s_score_round)
        b_level = risk_level(b_score_round)

        risk_change = round(s_score_round - b_score_round, 2)
        direction = "INCREASED" if risk_change > 0 else ("DECREASED" if risk_change < 0 else "UNCHANGED")

        top_factors, summary_text = get_dynamic_shap_explanation(mod_op_v3)

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

        return jsonify(res)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def analyze_site_internal(site_id, scenario_name=None):
    site_dict = site_registry.get_site(site_id)
    if not site_dict:
        site_dict = get_active_site_config()

    location = site_dict.get("city") or site_dict.get("city_name") or "Coimbatore"
    tx_id = site_dict.get("asset_ids", {}).get("transformer", "TX-001")
    sc_name = scenario_name or telemetry_mgr.active_scenario

    sample = get_live_data(tx_id)
    raw_op = sample.get("data", {})
    v3_op = sample.get("data_v3", raw_op)
    health_raw = sample.get("health_data", {})
    climate = get_climate(location, latitude=site_dict.get("latitude"), longitude=site_dict.get("longitude"))

    chiller_sample_dict = {}
    if chiller_df is not None and not chiller_df.empty:
        sample_idx = int(time.time() // 5) % len(chiller_df)
        chiller_sample_dict = chiller_df.iloc[sample_idx].to_dict()

    pump_sample_dict = {}
    if water_pump_df is not None and not water_pump_df.empty:
        sample_idx = int(time.time() // 5) % len(water_pump_df)
        pump_sample_dict = water_pump_df.iloc[sample_idx].to_dict()

    mod_raw_op, mod_v3_op, mod_health, mod_climate, deltas, meta = apply_scenario(
        sc_name, raw_op, v3_op, health_raw, climate, chiller_sample_dict, pump_sample_dict
    )
    mod_chiller = mod_climate.get("_mod_chiller", chiller_sample_dict)
    mod_pump = mod_climate.get("_mod_pump", pump_sample_dict)

    health_index, health_risk = predict_health(mod_health)
    op_risk = predict_operational(mod_v3_op)
    tx_health_contrib = round(health_risk * 0.40, 2)
    tx_op_contrib = round(op_risk * 0.40, 2)
    tx_climate_contrib = round(mod_climate["climate_stress"] * 0.20, 2)
    tx_cascade_risk = float(np.clip(tx_health_contrib + tx_op_contrib + tx_climate_contrib, 0, 100))
    tx_level = risk_level(tx_cascade_risk)

    transformer_schema = build_transformer_asset_schema(
        tx_cascade_risk, health_risk, op_risk, tx_level
    )

    chiller_risk = 5.0
    prob_normal = 0.95
    pred_class = 1
    prob_dict = {f"Class_{i}": 0.05 for i in range(1, 9)}
    prob_dict["Class_1"] = 0.95
    chiller_level = "NORMAL"

    if chiller_model is not None and chiller_features:
        ch_vals = [float(mod_chiller.get(feat, 0.0)) for feat in chiller_features]
        ch_X = pd.DataFrame([ch_vals], columns=chiller_features)
        ch_proba = chiller_model.predict_proba(ch_X)[0]
        
        normal_idx = int(chiller_mapping.get("normal_class_index", 0))
        prob_normal = float(ch_proba[normal_idx])
        pred_class_idx = int(np.argmax(ch_proba))
        pred_class = int(chiller_mapping.get("reverse_label_mapping", {}).get(str(pred_class_idx), pred_class_idx + 1))
        
        chiller_risk = round(float((1.0 - prob_normal) * 100.0), 2)
        chiller_level = risk_level(chiller_risk)

        for i, p in enumerate(ch_proba):
            orig_l = chiller_mapping.get("reverse_label_mapping", {}).get(str(i), i + 1)
            prob_dict[f"Class_{orig_l}"] = round(float(p), 4)

    chiller_schema = build_chiller_asset_schema(
        chiller_risk, pred_class, prob_normal, prob_dict, chiller_level
    )

    pump_risk = 15.0
    pred_state = "NORMAL"
    pump_level = "LOW"

    if water_pump_model is not None and water_pump_features:
        p_vals = [float(mod_pump.get(feat, 0.0)) for feat in water_pump_features]
        p_X = pd.DataFrame([p_vals], columns=water_pump_features)
        try:
            p_proba = water_pump_model.predict_proba(p_X)[0]
            pump_risk = round(float((p_proba[1]*0.33 + p_proba[2]*0.66 + p_proba[3]*1.00) * 100.0), 2)
            state_idx = int(np.argmax(p_proba))
            state_map = {0: "NORMAL", 1: "WATCH", 2: "WARNING", 3: "CRITICAL"}
            pred_state = state_map.get(state_idx, "NORMAL")
        except Exception:
            pump_risk = 20.0

    pump_schema = build_water_pump_asset_schema(pump_risk, pred_state, pump_level)

    cascade_eval = evaluate_cascade_graph(
        transformer_schema, chiller_schema, pump_schema, mod_climate
    )

    eval_payload = {
        "site": site_dict,
        "system": cascade_eval["system"],
        "assets": {
            "transformer": transformer_schema,
            "chiller": chiller_schema,
            "water_pump": pump_schema
        },
        "climate": mod_climate
    }
    live_telemetry = telemetry_mgr.get_all_live_telemetry()
    active_inc = incident_engine.evaluate_telemetry_incident(eval_payload, live_telemetry, sc_name)

    alert_result = None
    if active_inc and active_inc.get("severity") == "CRITICAL" and active_inc.get("status") == "OPEN":
        alert_result = alert_manager.dispatch_alert(active_inc)

    return {
        "success": True,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "site": site_dict,
        "location": location,
        "tx_id": tx_id,
        "scenario": meta,
        "climate": mod_climate,
        "assets": {
            "transformer": transformer_schema,
            "chiller": chiller_schema,
            "water_pump": pump_schema
        },
        "system": cascade_eval["system"],
        "cascade": cascade_eval["cascade"],
        "recommendation": cascade_eval["recommendation"],
        "limitations": cascade_eval["limitations"],
        "active_incident": active_inc,
        "alert_result": alert_result,
        "data_confidence": {
            "status": "LIVE",
            "confidence": "HIGH",
            "freshness": "REALTIME"
        }
    }


@app.route("/api/multi-asset-analyze", methods=["GET", "POST"])
def multi_asset_analyze():
    try:
        if request.method == "POST":
            req_data = request.get_json() or {}
        else:
            req_data = request.args.to_dict()

        site_id = req_data.get("site_id") or get_active_site_config().get("site_id", "SITE-001")
        scenario_name = req_data.get("scenario")
        res = analyze_site_internal(site_id, scenario_name=scenario_name)
        return jsonify(res)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# PHASE 10: REAL API ADAPTER & LIVE STATUS ENDPOINTS
# ============================================================

weather_client_inst = WeatherAPIClient()
transformer_client_inst = TransformerTelemetryClient()
chiller_client_inst = ChillerTelemetryClient()
water_pump_client_inst = WaterPumpTelemetryClient()
telemetry_mgr = TelemetryManager()
incident_engine = IncidentEngine()
alert_manager = AlertManager()


# ============================================================
# PHASE 13: INCIDENT INTELLIGENCE & ALERTING ENDPOINTS
# ============================================================

@app.route("/api/incidents", methods=["GET"])
def get_incidents_endpoint():
    data = incident_engine.get_all_incidents()
    return jsonify({
        "success": True,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "active_incidents_count": len(data.get("active_incidents", [])),
        "resolved_incidents_count": len(data.get("resolved_incidents", [])),
        "data": data
    })


@app.route("/api/incidents/<incident_id>", methods=["GET"])
def get_single_incident_endpoint(incident_id):
    inc = incident_engine.get_incident_by_id(str(incident_id).strip())
    if not inc:
        return jsonify({"success": False, "error": f"Incident ID '{incident_id}' not found"}), 404
    return jsonify({
        "success": True,
        "incident": inc
    })


@app.route("/api/incidents/<incident_id>/acknowledge", methods=["POST"])
def acknowledge_incident_endpoint(incident_id):
    is_ok, inc = incident_engine.acknowledge_incident(str(incident_id).strip())
    if not is_ok:
        return jsonify({"success": False, "error": f"Incident ID '{incident_id}' not found"}), 404
    return jsonify({
        "success": True,
        "message": f"Incident '{incident_id}' acknowledged successfully",
        "incident": inc
    })


@app.route("/api/incidents/<incident_id>/resolve", methods=["POST"])
def resolve_incident_endpoint(incident_id):
    is_ok, inc = incident_engine.resolve_incident(str(incident_id).strip())
    if not is_ok:
        return jsonify({"success": False, "error": f"Incident ID '{incident_id}' not found"}), 404
    return jsonify({
        "success": True,
        "message": f"Incident '{incident_id}' resolved successfully",
        "incident": inc
    })


@app.route("/api/incidents/generate-report", methods=["POST"])
def generate_incident_report_endpoint():
    try:
        data = request.get_json() or {}
        inc_id = data.get("incident_id")
        
        inc = None
        if inc_id:
            inc = incident_engine.get_incident_by_id(str(inc_id).strip())
        
        # If incident not specified or not found, build sample report for active incident
        if not inc:
            all_inc = incident_engine.get_all_incidents()
            active_list = all_inc.get("active_incidents", [])
            history_list = all_inc.get("history", [])
            if active_list:
                inc = active_list[0]
            elif history_list:
                inc = history_list[0]
            else:
                inc = {
                    "incident_id": "INC-2026-DEMO-001",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "severity": "WARNING",
                    "status": "OPEN",
                    "system_risk": 55.4,
                    "most_vulnerable_asset": "CHILLER",
                    "affected_assets": {"transformer_risk": 42.0, "chiller_risk": 68.0, "water_pump_risk": 35.0},
                    "trigger": "Demo Incident Executive Report",
                    "cascade_path": "Climate Stress ➔ Water Pump ➔ Chiller ➔ Transformer ➔ System Cascade Risk",
                    "data_sources": {
                        "climate": "LIVE_OPEN_METEO_API",
                        "transformer": "HISTORICAL_REPLAY",
                        "chiller": "HISTORICAL_DATASET",
                        "water_pump": "HISTORICAL_DATASET (DECISION SUPPORT ONLY)"
                    }
                }

        filename = f"CascadeGuard_Incident_{inc.get('incident_id', 'Report')}.pdf"
        return _flask_pdf_response(inc, filename)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


def _flask_pdf_response(inc_dict, filename):
    try:
        pdf_bytes = generate_pdf_report(inc_dict)
        if not pdf_bytes or len(pdf_bytes) == 0 or not pdf_bytes.startswith(b"%PDF-"):
            return jsonify({"status": "error", "message": "Generated report is not a valid PDF file"}), 500

        if not filename.lower().endswith(".pdf"):
            filename = f"{filename}.pdf"

        res = send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename
        )
        res.headers["Content-Type"] = "application/pdf"
        res.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        return res
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/reports/executive", methods=["GET", "POST"])
def executive_report_flask():
    return _flask_pdf_response(incident_engine.get_all_incidents().get("active_incidents", [{}])[0] or {}, "CascadeGuard_Executive_Report.pdf")


@app.route("/api/reports/regional", methods=["GET", "POST"])
def regional_report_flask():
    return _flask_pdf_response(incident_engine.get_all_incidents().get("active_incidents", [{}])[0] or {}, "CascadeGuard_Regional_Report.pdf")


@app.route("/api/reports/fleet", methods=["GET", "POST"])
def fleet_report_flask():
    return _flask_pdf_response(incident_engine.get_all_incidents().get("active_incidents", [{}])[0] or {}, "CascadeGuard_Fleet_Report.pdf")


@app.route("/api/reports/incident", methods=["GET", "POST"])
def incident_report_flask():
    inc_id = request.args.get("incident_id") or (request.get_json(silent=True) or {}).get("incident_id")
    inc = incident_engine.get_incident_by_id(inc_id) if inc_id else None
    if not inc:
        inc = incident_engine.get_all_incidents().get("active_incidents", [{}])[0] or {}
    fname = f"CascadeGuard_Incident_{inc_id}.pdf" if inc_id else "CascadeGuard_Incident_Report.pdf"
    return _flask_pdf_response(inc, fname)


@app.route("/api/alerts/status", methods=["GET"])
def alert_status_endpoint():
    return jsonify({
        "success": True,
        "alert_status": alert_manager.get_status()
    })


@app.route("/api/incidents/test-alert", methods=["POST"])
def test_alert_endpoint():
    try:
        sample_inc = {
            "incident_id": "INC-TEST-999",
            "severity": "CRITICAL",
            "system_risk": 82.4,
            "most_vulnerable_asset": "CHILLER",
            "trigger": "Manual API Webhook Test Trigger",
            "data_sources": {"climate": "LIVE_OPEN_METEO_API"}
        }
        res = alert_manager.dispatch_alert(sample_inc)
        return jsonify({
            "success": True,
            "dispatch_result": res
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# PHASE 12: REAL-TIME INDUSTRIAL OT CONNECTIVITY ENDPOINTS
# ============================================================

@app.route("/api/telemetry/status", methods=["GET"])
def telemetry_status_endpoint():
    return jsonify({
        "success": True,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "telemetry_mode": telemetry_mgr.mode,
        "active_scenario": telemetry_mgr.active_scenario,
        "assets": telemetry_mgr.get_status()
    })


@app.route("/api/telemetry/live", methods=["GET"])
def telemetry_live_endpoint():
    return jsonify({
        "success": True,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "telemetry_mode": telemetry_mgr.mode,
        "active_scenario": telemetry_mgr.active_scenario,
        "telemetry": telemetry_mgr.get_all_live_telemetry()
    })


@app.route("/api/telemetry/mode", methods=["POST"])
def telemetry_mode_endpoint():
    try:
        data = request.get_json() or {}
        req_mode = data.get("mode")
        if not req_mode:
            return jsonify({"success": False, "error": "Missing required parameter: mode"}), 400

        is_ok = telemetry_mgr.set_mode(req_mode)
        if not is_ok:
            return jsonify({"success": False, "error": f"Invalid telemetry mode '{req_mode}'. Allowed values: ['MOCK', 'REAL_OT']"}), 400

        return jsonify({
            "success": True,
            "telemetry_mode": telemetry_mgr.mode,
            "status": telemetry_mgr.get_status()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/telemetry/scenario", methods=["POST"])
def telemetry_scenario_endpoint():
    try:
        data = request.get_json() or {}
        req_scenario = data.get("scenario")
        if not req_scenario:
            return jsonify({"success": False, "error": "Missing required parameter: scenario"}), 400

        is_ok = telemetry_mgr.set_scenario(req_scenario)
        if not is_ok:
            return jsonify({"success": False, "error": f"Invalid scenario '{req_scenario}'. Allowed values: ['NORMAL', 'HIGH_LOAD', 'HEAT_STRESS', 'CHILLER_OVERLOAD', 'PUMP_DEGRADATION', 'COMBINED_CASCADE']"}), 400

        return jsonify({
            "success": True,
            "active_scenario": telemetry_mgr.active_scenario,
            "live_telemetry": telemetry_mgr.get_all_live_telemetry()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/telemetry/asset/<asset_id>", methods=["GET"])
def telemetry_single_asset_endpoint(asset_id):
    try:
        aid = str(asset_id).upper()
        category = "transformer"
        if "CH" in aid:
            category = "chiller"
        elif "WP" in aid or "PUMP" in aid:
            category = "water_pump"

        data = telemetry_mgr.get_asset_telemetry(category, aid)
        return jsonify({
            "success": True,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "telemetry": data
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# PHASE 11A: PRECISE SITE LOCATION & CONFIGURATION ENDPOINTS
# ============================================================

@app.route("/api/site/configure", methods=["POST"])
def site_configure_endpoint():
    try:
        data = request.get_json() or {}
        is_ok, err_msg, norm_site = validate_site_config(data)
        if not is_ok:
            return jsonify({"success": False, "error": err_msg}), 400

        set_active_site_config(norm_site)
        return jsonify({
            "success": True,
            "site": norm_site
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/site/config", methods=["GET"])
def site_config_endpoint():
    site = get_active_site_config()
    if not site:
        return jsonify({"success": False, "configured": False}), 404
    return jsonify({
        "success": True,
        "configured": True,
        "site": site
    })


@app.route("/api/climate", methods=["GET"])
@app.route("/api/climate-intelligence", methods=["GET"])
def climate_intelligence_endpoint():
    try:
        site_id = request.args.get("site_id")
        if site_id:
            site = site_registry.get_site(site_id)
            if not site:
                return jsonify({"success": False, "error": f"Site '{site_id}' not found."}), 404
            
            lat = site["latitude"]
            lon = site["longitude"]
            location = site.get("city", site.get("site_name", "Coimbatore"))
            site_cfg = {
                "site_id": site["site_id"],
                "site_name": site["site_name"],
                "city": location,
                "location": {"name": location, "latitude": lat, "longitude": lon},
                "assets": site.get("asset_ids", {"transformer_id": f"TX-{site['site_id']}", "chiller_id": f"CH-{site['site_id']}", "water_pump_id": f"WP-{site['site_id']}"}),
                "climate_thresholds": {"heatwave_threshold_temp": 35.0, "heatwave_threshold_hours": 3}
            }
        else:
            site_cfg = get_active_site_config()
            location = request.args.get("location", site_cfg["location"]["name"])
            
            lat_arg = request.args.get("latitude")
            lon_arg = request.args.get("longitude")
            if lat_arg is not None or lon_arg is not None:
                lat_val = lat_arg if lat_arg is not None else site_cfg["location"]["latitude"]
                lon_val = lon_arg if lon_arg is not None else site_cfg["location"]["longitude"]
                is_valid, err = validate_coordinates(lat_val, lon_val)
                if not is_valid:
                    return jsonify({"success": False, "error": err}), 400
                lat, lon = float(lat_val), float(lon_val)
            else:
                lat = site_cfg["location"]["latitude"]
                lon = site_cfg["location"]["longitude"]

        w_norm = weather_client_inst.get_current_data(location=location, latitude=lat, longitude=lon, site_id=site_cfg.get("site_id", "SITE-001"))
        raw_weather = w_norm["data"]

        intel = analyze_climate_intelligence(raw_weather, site_cfg)
        return jsonify({
            "success": True,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "site": site_cfg,
            "climate_intelligence": intel
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/live", methods=["GET"])
def live_alias_endpoint():
    return realtime_status_endpoint()


@app.route("/api/realtime-status", methods=["GET"])
def realtime_status_endpoint():
    site_id = request.args.get("site_id")
    if site_id:
        site = site_registry.get_site(site_id)
        if not site:
            return jsonify({"success": False, "error": f"Site '{site_id}' not found."}), 404
        site_cfg = {
            "site_id": site["site_id"],
            "site_name": site["site_name"],
            "city": site.get("city", "Coimbatore"),
            "location": {"name": site.get("city", "Coimbatore"), "latitude": site["latitude"], "longitude": site["longitude"]},
            "assets": site.get("asset_ids", {"transformer_id": f"TX-{site['site_id']}", "chiller_id": f"CH-{site['site_id']}", "water_pump_id": f"WP-{site['site_id']}"})
        }
    else:
        site_cfg = get_active_site_config()

    w_norm = weather_client_inst.get_current_data(location=site_cfg["location"]["name"], latitude=site_cfg["location"]["latitude"], longitude=site_cfg["location"]["longitude"], site_id=site_cfg.get("site_id", "SITE-001"))
    intel = analyze_climate_intelligence(w_norm["data"], site_cfg)

    return jsonify({
        "success": True,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "site": site_cfg,
        "weather": weather_client_inst.get_status(),
        "transformer": transformer_client_inst.get_status(),
        "chiller": chiller_client_inst.get_status(),
        "water_pump": water_pump_client_inst.get_status(),
        "climate_intelligence": intel
    })


@app.route("/api/realtime-analyze", methods=["GET", "POST"])
def realtime_analyze_endpoint():
    try:
        if request.method == "POST":
            req_data = request.get_json() or {}
        else:
            req_data = request.args.to_dict()

        site_id = req_data.get("site_id")
        if site_id:
            site = site_registry.get_site(site_id)
            if not site:
                return jsonify({"success": False, "error": f"Site '{site_id}' not found."}), 404
            site_cfg = {
                "site_id": site["site_id"],
                "site_name": site["site_name"],
                "city": site.get("city", "Coimbatore"),
                "location": {"name": site.get("city", "Coimbatore"), "latitude": site["latitude"], "longitude": site["longitude"]},
                "assets": site.get("asset_ids", {"transformer_id": f"TX-{site['site_id']}", "chiller_id": f"CH-{site['site_id']}", "water_pump_id": f"WP-{site['site_id']}"})
            }
        else:
            site_cfg = get_active_site_config()

        location = req_data.get("location", site_cfg["location"]["name"])
        
        lat_val = req_data.get("latitude", site_cfg["location"]["latitude"])
        lon_val = req_data.get("longitude", site_cfg["location"]["longitude"])
        if "latitude" in req_data or "longitude" in req_data:
            is_valid, err = validate_coordinates(lat_val, lon_val)
            if not is_valid:
                return jsonify({"success": False, "error": err}), 400
        lat = float(lat_val)
        lon = float(lon_val)

        tx_id = req_data.get("tx_id", site_cfg["assets"]["transformer_id"])

        # 1. Weather API Client (Using Exact Coordinates)
        weather_normalized = weather_client_inst.get_current_data(location=location, latitude=lat, longitude=lon, site_id=site_cfg.get("site_id", "SITE-001"))
        climate_data = weather_normalized["data"]

        # 2. Transformer Telemetry Client
        tx_sample = get_live_data(tx_id)
        tx_normalized = transformer_client_inst.get_current_data(tx_id=tx_id, replay_sample=tx_sample)
        
        mod_v3_op = tx_sample.get("data_v3", tx_sample.get("data", {}))
        mod_health = tx_sample.get("health_data", {})
        health_idx, health_rk = predict_health(mod_health)
        op_rk = predict_operational(mod_v3_op)
        tx_health_contrib = round(health_rk * 0.40, 2)
        tx_op_contrib = round(op_rk * 0.40, 2)
        tx_climate_contrib = round(climate_data.get("climate_stress", 19.7) * 0.20, 2)
        tx_cascade_risk = float(np.clip(tx_health_contrib + tx_op_contrib + tx_climate_contrib, 0, 100))
        tx_level = risk_level(tx_cascade_risk)
        
        transformer_schema = build_transformer_asset_schema(
            tx_cascade_risk, health_risk=health_rk, op_risk=op_rk, level=tx_level
        )
        transformer_schema["provenance"] = tx_normalized["source"]
        transformer_schema["freshness"] = tx_normalized["quality"]

        # 3. Chiller Telemetry Client
        chiller_sample_dict = {}
        if chiller_df is not None and len(chiller_df) > 0:
            s_idx = int(time.time() // 5) % len(chiller_df)
            chiller_sample_dict = chiller_df.iloc[s_idx].to_dict()
        chiller_normalized = chiller_client_inst.get_current_data(chiller_sample=chiller_sample_dict)

        chiller_risk = 5.0
        prob_normal = 0.95
        pred_class = 1
        prob_dict = {f"Class_{i}": 0.05 for i in range(1, 9)}
        prob_dict["Class_1"] = 0.95
        chiller_level = "NORMAL"

        if chiller_model is not None and chiller_features:
            ch_vals = [float(chiller_sample_dict.get(feat, 0.0)) for feat in chiller_features]
            ch_X = pd.DataFrame([ch_vals], columns=chiller_features)
            ch_proba = chiller_model.predict_proba(ch_X)[0]
            normal_idx = int(chiller_mapping.get("normal_class_index", 0))
            prob_normal = float(ch_proba[normal_idx])
            pred_class_idx = int(np.argmax(ch_proba))
            pred_class = int(chiller_mapping.get("reverse_label_mapping", {}).get(str(pred_class_idx), pred_class_idx + 1))
            chiller_risk = round(float((1.0 - prob_normal) * 100.0), 2)
            chiller_level = risk_level(chiller_risk)
            for i, p in enumerate(ch_proba):
                orig_l = chiller_mapping.get("reverse_label_mapping", {}).get(str(i), i + 1)
                prob_dict[f"Class_{orig_l}"] = round(float(p), 4)

        chiller_schema = build_chiller_asset_schema(
            chiller_risk, pred_class, prob_normal, prob_dict, chiller_level
        )
        chiller_schema["provenance"] = chiller_normalized["source"]
        chiller_schema["freshness"] = chiller_normalized["quality"]

        # 4. Water Pump Telemetry Client (Decision Support Only)
        pump_sample_dict = {}
        if water_pump_df is not None and len(water_pump_df) > 0:
            s_idx = int(time.time() // 5) % len(water_pump_df)
            pump_sample_dict = water_pump_df.iloc[s_idx].to_dict()
        pump_normalized = water_pump_client_inst.get_current_data(pump_sample=pump_sample_dict)

        pump_risk = 15.0
        pred_state = "NORMAL"
        pump_level = "LOW"

        if water_pump_model is not None and water_pump_features:
            p_vals = [float(pump_sample_dict.get(feat, 0.0)) for feat in water_pump_features]
            p_X = pd.DataFrame([p_vals], columns=water_pump_features)
            try:
                p_proba = water_pump_model.predict_proba(p_X)[0]
                pump_risk = round(float((p_proba[1]*0.33 + p_proba[2]*0.66 + p_proba[3]*1.00) * 100.0), 2)
                state_idx = int(np.argmax(p_proba))
                state_map = {0: "NORMAL", 1: "WATCH", 2: "WARNING", 3: "CRITICAL"}
                pred_state = state_map.get(state_idx, "NORMAL")
            except Exception:
                pump_risk = 20.0

        pump_schema = build_water_pump_asset_schema(pump_risk, pred_state, pump_level)
        pump_schema["provenance"] = pump_normalized["source"]
        pump_schema["freshness"] = pump_normalized["quality"]

        # 5. Evaluate System Cascade Engine
        cascade_eval = evaluate_cascade_graph(
            transformer_schema, chiller_schema, pump_schema, climate_data
        )

        intel = analyze_climate_intelligence(climate_data, site_cfg)

        return jsonify({
            "success": True,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "site": site_cfg,
            "climate_intelligence": intel,
            "data_sources": {
                "weather": weather_client_inst.get_status(),
                "transformer": transformer_client_inst.get_status(),
                "chiller": chiller_client_inst.get_status(),
                "water_pump": water_pump_client_inst.get_status()
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
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# PHASE 11: CLIMATE STRESS WHAT-IF SIMULATION ENDPOINTS
# ============================================================

@app.route("/api/scenario-analyze", methods=["GET", "POST"])
def scenario_analyze_endpoint():
    try:
        if request.method == "POST":
            req_data = request.get_json() or {}
        else:
            req_data = request.args.to_dict()

        location = req_data.get("location", "Coimbatore")
        scenario_name = req_data.get("scenario", "HEATWAVE")
        tx_id = req_data.get("tx_id", "TX-001")

        # 1. Fetch Live Weather Baseline
        weather_normalized = weather_client_inst.get_current_data(location)
        baseline_climate = weather_normalized["data"]

        # 2. Apply What-If Climate Transformation
        climate_res = apply_climate_scenario_transform(baseline_climate, scenario_name)

        # 3. Retrieve Baseline Asset Schemas & Data
        tx_sample = get_live_data(tx_id)
        mod_v3_op = tx_sample.get("data_v3", tx_sample.get("data", {}))
        mod_health = tx_sample.get("health_data", {})
        health_idx, health_rk = predict_health(mod_health)
        op_rk = predict_operational(mod_v3_op)
        tx_health_contrib = round(health_rk * 0.40, 2)
        tx_op_contrib = round(op_rk * 0.40, 2)
        tx_climate_contrib = round(baseline_climate.get("climate_stress", 19.7) * 0.20, 2)
        tx_cascade_risk = float(np.clip(tx_health_contrib + tx_op_contrib + tx_climate_contrib, 0, 100))
        tx_level = risk_level(tx_cascade_risk)
        transformer_schema = build_transformer_asset_schema(tx_cascade_risk, health_risk=health_rk, op_risk=op_rk, level=tx_level)

        # Chiller Baseline
        chiller_sample_dict = {}
        if chiller_df is not None and len(chiller_df) > 0:
            s_idx = int(time.time() // 5) % len(chiller_df)
            chiller_sample_dict = chiller_df.iloc[s_idx].to_dict()

        chiller_risk = 5.0
        prob_normal = 0.95
        pred_class = 1
        prob_dict = {f"Class_{i}": 0.05 for i in range(1, 9)}
        prob_dict["Class_1"] = 0.95
        chiller_level = "NORMAL"

        if chiller_model is not None and chiller_features:
            ch_vals = [float(chiller_sample_dict.get(feat, 0.0)) for feat in chiller_features]
            ch_X = pd.DataFrame([ch_vals], columns=chiller_features)
            ch_proba = chiller_model.predict_proba(ch_X)[0]
            normal_idx = int(chiller_mapping.get("normal_class_index", 0))
            prob_normal = float(ch_proba[normal_idx])
            pred_class_idx = int(np.argmax(ch_proba))
            pred_class = int(chiller_mapping.get("reverse_label_mapping", {}).get(str(pred_class_idx), pred_class_idx + 1))
            chiller_risk = round(float((1.0 - prob_normal) * 100.0), 2)
            chiller_level = risk_level(chiller_risk)
            for i, p in enumerate(ch_proba):
                orig_l = chiller_mapping.get("reverse_label_mapping", {}).get(str(i), i + 1)
                prob_dict[f"Class_{orig_l}"] = round(float(p), 4)

        chiller_schema = build_chiller_asset_schema(chiller_risk, pred_class, prob_normal, prob_dict, chiller_level)

        # Water Pump Baseline
        pump_sample_dict = {}
        if water_pump_df is not None and len(water_pump_df) > 0:
            s_idx = int(time.time() // 5) % len(water_pump_df)
            pump_sample_dict = water_pump_df.iloc[s_idx].to_dict()

        pump_risk = 15.0
        pred_state = "NORMAL"
        pump_level = "LOW"

        if water_pump_model is not None and water_pump_features:
            p_vals = [float(pump_sample_dict.get(feat, 0.0)) for feat in water_pump_features]
            p_X = pd.DataFrame([p_vals], columns=water_pump_features)
            try:
                p_proba = water_pump_model.predict_proba(p_X)[0]
                pump_risk = round(float((p_proba[1]*0.33 + p_proba[2]*0.66 + p_proba[3]*1.00) * 100.0), 2)
                state_idx = int(np.argmax(p_proba))
                state_map = {0: "NORMAL", 1: "WATCH", 2: "WARNING", 3: "CRITICAL"}
                pred_state = state_map.get(state_idx, "NORMAL")
            except Exception:
                pump_risk = 20.0

        pump_schema = build_water_pump_asset_schema(pump_risk, pred_state, pump_level)

        # 4. Evaluate Cascade What-If Scenario
        scenario_eval = evaluate_cascade_scenario(
            transformer_schema, chiller_schema, pump_schema, climate_res
        )

        return jsonify({
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
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/scenario-summary", methods=["GET"])
def scenario_summary_endpoint():
    try:
        site_cfg = get_active_site_config()
        location = request.args.get("location", site_cfg["location"]["name"])
        lat = request.args.get("latitude", site_cfg["location"]["latitude"])
        lon = request.args.get("longitude", site_cfg["location"]["longitude"])
        tx_id = request.args.get("tx_id", site_cfg["assets"]["transformer_id"])

        all_scenarios = get_supported_climate_scenarios()
        summary_list = []

        w_norm = weather_client_inst.get_current_data(location=location, latitude=lat, longitude=lon)
        b_clim = w_norm["data"]

        tx_sample = get_live_data(tx_id)
        mod_v3_op = tx_sample.get("data_v3", tx_sample.get("data", {}))
        mod_health = tx_sample.get("health_data", {})
        _, health_rk = predict_health(mod_health)
        op_rk = predict_operational(mod_v3_op)
        tx_contrib = round(health_rk * 0.40 + op_rk * 0.40 + b_clim.get("climate_stress", 19.7) * 0.20, 2)
        tx_schema = build_transformer_asset_schema(tx_contrib, health_rk, op_rk, risk_level(tx_contrib))
        ch_schema = build_chiller_asset_schema(22.4, 1, 0.95, {}, "NORMAL")
        wp_schema = build_water_pump_asset_schema(20.0, "NORMAL", "LOW")

        for sc_meta in all_scenarios:
            sc_name = sc_meta["name"]
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

        return jsonify({
            "success": True,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "site": site_cfg,
            "location": location,
            "scenarios": summary_list
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analyze", methods=["POST"])
def analyze():
    try:
        data = request.get_json() or {}
        location = data.get("location", "Coimbatore")

        health_index, health_risk = predict_health(data)
        operational_risk = predict_operational(data)
        climate = get_climate(location)

        health_contrib = round(health_risk * 0.40, 2)
        op_contrib = round(operational_risk * 0.40, 2)
        climate_contrib = round(climate["climate_stress"] * 0.20, 2)

        final_risk = float(np.clip(health_contrib + op_contrib + climate_contrib, 0, 100))
        final_risk_round = round(final_risk, 2)
        level = risk_level(final_risk_round)
        recommendation = get_recommendation(level)

        top_factors, summary_text = get_dynamic_shap_explanation(data)

        return jsonify({
            "success": True,
            "operational_model_version": operational_model_version,
            "health": {
                "index": round(health_index, 2),
                "risk": round(health_risk, 2)
            },
            "operational": {
                "risk": round(operational_risk, 2)
            },
            "climate": climate,
            "cascade": {
                "score": final_risk_round,
                "level": level
            },
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
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================
# PHASE 14: MULTI-SITE & REGIONAL COMMAND CENTER ENDPOINTS
# ============================================================

@app.route("/api/sites", methods=["GET"])
def get_sites():
    sites = site_registry.get_all_sites()
    return jsonify({
        "success": True,
        "count": len(sites),
        "sites": sites
    })

@app.route("/api/sites/<site_id>", methods=["GET"])
def get_site_details(site_id):
    site = site_registry.get_site(site_id)
    if not site:
        return jsonify({"success": False, "error": f"Site '{site_id}' not found."}), 404
    return jsonify({"success": True, "site": site})

@app.route("/api/sites", methods=["POST"])
def create_site():
    req_data = request.get_json() or {}
    ok, msg, new_site = site_registry.add_site(req_data)
    if not ok:
        return jsonify({"success": False, "error": msg}), 400
    return jsonify({"success": True, "message": msg, "site": new_site}), 201

@app.route("/api/sites/<site_id>", methods=["PUT"])
def update_site_endpoint(site_id):
    req_data = request.get_json() or {}
    ok, msg, updated_site = site_registry.update_site(site_id, req_data)
    if not ok:
        status_code = 404 if "not found" in msg.lower() else 400
        return jsonify({"success": False, "error": msg}), status_code
    return jsonify({"success": True, "message": msg, "site": updated_site})

@app.route("/api/sites/<site_id>", methods=["DELETE"])
def delete_site_endpoint(site_id):
    ok, msg = site_registry.delete_site(site_id)
    if not ok:
        return jsonify({"success": False, "error": msg}), 404
    return jsonify({"success": True, "message": msg})

@app.route("/api/sites/<site_id>/activate", methods=["POST"])
def activate_site_endpoint(site_id):
    ok, msg = site_registry.activate_site(site_id)
    if not ok:
        return jsonify({"success": False, "error": msg}), 404
    return jsonify({"success": True, "message": msg})

@app.route("/api/sites/<site_id>/deactivate", methods=["POST"])
def deactivate_site_endpoint(site_id):
    ok, msg = site_registry.deactivate_site(site_id)
    if not ok:
        return jsonify({"success": False, "error": msg}), 404
    return jsonify({"success": True, "message": msg})

@app.route("/api/regional-status", methods=["GET"])
def regional_status_endpoint():
    active_sites = site_registry.get_all_sites(active_only=True)
    site_evals = []
    for s in active_sites:
        try:
            ev = analyze_site_internal(s["site_id"])
            site_evals.append(ev)
        except Exception as e:
            print(f"Error analyzing site {s['site_id']}:", e)

    regional_eval = regional_risk_engine.evaluate_regional_status(site_evals)
    return jsonify({
        "success": True,
        "regional": regional_eval
    })

@app.route("/api/sites/<site_id>/analyze", methods=["GET"])
def site_analyze_endpoint(site_id):
    site = site_registry.get_site(site_id)
    if not site:
        return jsonify({"success": False, "error": f"Site '{site_id}' not found."}), 404

    scenario_name = request.args.get("scenario")
    res = analyze_site_internal(site_id, scenario_name=scenario_name)
    return jsonify(res)

@app.route("/api/sites/<site_id>/climate", methods=["GET"])
def site_climate_endpoint(site_id):
    site = site_registry.get_site(site_id)
    if not site:
        return jsonify({"success": False, "error": f"Site '{site_id}' not found."}), 404

    lat = site["latitude"]
    lon = site["longitude"]
    location = site.get("city", site.get("site_name", "Coimbatore"))

    site_cfg = {
        "site_id": site["site_id"],
        "site_name": site["site_name"],
        "city": location,
        "location": {"name": location, "latitude": lat, "longitude": lon},
        "assets": site.get("asset_ids", {"transformer_id": f"TX-{site_id}", "chiller_id": f"CH-{site_id}", "water_pump_id": f"WP-{site_id}"}),
        "climate_thresholds": {"heatwave_threshold_temp": 35.0, "heatwave_threshold_hours": 3}
    }

    w_norm = weather_client_inst.get_current_data(location=location, latitude=lat, longitude=lon, site_id=site_id)
    intel = analyze_climate_intelligence(w_norm["data"], site_cfg)

    return jsonify({
        "success": True,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "site": site,
        "climate_intelligence": intel
    })

@app.route("/api/regional/incidents", methods=["GET"])
def regional_incidents_endpoint():
    all_incidents = incident_engine.get_incidents()
    history = all_incidents.get("history", [])

    sev_filter = request.args.get("severity")
    site_filter = request.args.get("site_id")
    stat_filter = request.args.get("status")

    filtered = history
    if sev_filter:
        filtered = [i for i in filtered if i.get("severity") == sev_filter.upper()]
    if site_filter:
        filtered = [i for i in filtered if i.get("site_id") == site_filter]
    if stat_filter:
        filtered = [i for i in filtered if i.get("status") == stat_filter.upper()]

    return jsonify({
        "success": True,
        "count": len(filtered),
        "incidents": filtered
    })

@app.route("/api/regional-history", methods=["GET"])
def regional_history_endpoint():
    history = regional_risk_engine.get_history()
    return jsonify({
        "success": True,
        "count": len(history),
        "history": history
    })

# STATIC FILE SERVING FOR FRONTEND & CORS
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response

@app.route("/", methods=["GET"])
def index_page():
    frontend_dir = os.path.join(PROJECT_ROOT, "frontend")
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return send_file(index_path)
    return jsonify({"success": True, "message": "CascadeGuard AI API Engine Server"})

@app.route("/<path:path>", methods=["GET"])
def serve_static(path):
    if path.startswith("api/"):
        return jsonify({"success": False, "error": "Endpoint not found"}), 404
    frontend_dir = os.path.join(PROJECT_ROOT, "frontend")
    file_path = os.path.join(frontend_dir, path)
    if os.path.exists(file_path):
        return send_file(file_path)
    return jsonify({"success": False, "error": "File not found"}), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print("=" * 60)
    print(f"CASCADEGUARD MULTI-ASSET COMMAND CENTER")
    print(f"Server Running on: http://127.0.0.1:{port}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)
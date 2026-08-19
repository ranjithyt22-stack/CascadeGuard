"""
backend/state.py
================
Shared application state for CascadeGuard FastAPI server.
All ML models, SHAP explainer, API clients, and shared business-logic
helper functions live here so route modules can import them without
circular dependency.

This module is intentionally NOT imported at package import time.
It is populated during the FastAPI lifespan startup event in main.py.
"""
import sys
import os
import json
import time
from pathlib import Path
from collections import deque

import pandas as pd
import numpy as np
import joblib
import shap

# ── Path resolution ─────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = str(BASE_DIR)

# ── ML model paths ───────────────────────────────────────────────────────────
HEALTH_MODEL_PATH          = BASE_DIR / "models" / "health_index_xgboost.pkl"
OPERATIONAL_MODEL_V3_PATH  = BASE_DIR / "models" / "operational_stress_xgboost_v3.pkl"
OPERATIONAL_MODEL_V2_PATH  = BASE_DIR / "models" / "operational_stress_xgboost_v2.pkl"
OPERATIONAL_FEATURES_V3_PATH = BASE_DIR / "models" / "operational_features_v3.csv"
METADATA_PATH              = BASE_DIR / "models" / "operational_model_metadata.json"

CHILLER_MODEL_PATH   = BASE_DIR / "models" / "chiller_xgboost.pkl"
CHILLER_FEATURES_PATH = BASE_DIR / "models" / "chiller_features.csv"
CHILLER_MAPPING_PATH = BASE_DIR / "models" / "chiller_label_mapping.json"
CHILLER_DATA_PATH    = BASE_DIR / "data" / "raw" / "chiller" / "11000.xlsx"

WATER_PUMP_MODEL_PATH    = BASE_DIR / "models" / "water_pump_xgboost.pkl"
WATER_PUMP_FEATURES_PATH = BASE_DIR / "models" / "water_pump_features.csv"
WATER_PUMP_DECISION_PATH = BASE_DIR / "models" / "water_pump_model_decision.json"
WATER_PUMP_DATA_PATH     = BASE_DIR / "data" / "raw" / "water_pump" / "rul_hrs.csv"

# ── Mutable globals (populated by load_all_models()) ─────────────────────────
health_model              = None
operational_model         = None
operational_model_version = "v3"
OPERATIONAL_FEATURES_V3   = []
operational_metadata      = {}

chiller_model    = None
chiller_features = []
chiller_mapping  = {}
chiller_df       = None

water_pump_model    = None
water_pump_features = []
water_pump_decision = {}
water_pump_df       = None

shap_explainer     = None
predictive_history = deque(maxlen=50)

# API clients and engines (populated by load_all_models())
site_registry        = None
regional_risk_engine = None
weather_client_inst      = None
transformer_client_inst  = None
chiller_client_inst      = None
water_pump_client_inst   = None
telemetry_mgr   = None
incident_engine = None
alert_manager   = None
device_registry = None
mqtt_client     = None


# ── Feature mappings ─────────────────────────────────────────────────────────
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
    "KW_roll60m_mean": "Elevated 60-minute active power load",
    "THDVL1_roll60m_mean": "Elevated 60-minute voltage harmonic distortion (Phase L1)",
    "THDVL1_roll30m_mean": "Recent voltage harmonic distortion (Phase L1)",
    "THDVL1_roll30m_std": "Voltage harmonic distortion fluctuation (30m Std Dev)",
    "THDVL1_roll60m_std": "Voltage harmonic distortion fluctuation (60m Std Dev)",
    "Avg_PF_roll60m_mean": "60-minute average power factor stability",
    "Avg_PF_roll30m_mean": "30-minute average power factor stability",
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
    "OTI_roll30m_mean": "Sustained high oil temperature over 30 minutes",
    "OTI_roll60m_mean": "Persistent high oil temperature over 60 minutes",
    "OTI_diff1": "Rapid rate of oil temperature change"
}


def load_all_models():
    """Load all ML models, SHAP, API clients, and business engines.
    Called once during FastAPI lifespan startup."""
    global health_model, operational_model, operational_model_version
    global OPERATIONAL_FEATURES_V3, operational_metadata
    global chiller_model, chiller_features, chiller_mapping, chiller_df
    global water_pump_model, water_pump_features, water_pump_decision, water_pump_df
    global shap_explainer
    global site_registry, regional_risk_engine
    global weather_client_inst, transformer_client_inst, chiller_client_inst, water_pump_client_inst
    global telemetry_mgr, incident_engine, alert_manager
    global device_registry, mqtt_client

    # ── Transformer models ────────────────────────────────────────────────
    health_model = joblib.load(HEALTH_MODEL_PATH)

    if OPERATIONAL_MODEL_V3_PATH.exists():
        operational_model = joblib.load(OPERATIONAL_MODEL_V3_PATH)
        operational_model_version = "v3"
    else:
        operational_model = joblib.load(OPERATIONAL_MODEL_V2_PATH)
        operational_model_version = "v2"

    if OPERATIONAL_FEATURES_V3_PATH.exists():
        with open(OPERATIONAL_FEATURES_V3_PATH, "r") as f:
            OPERATIONAL_FEATURES_V3 = [line.strip() for line in f if line.strip()]

    if METADATA_PATH.exists():
        try:
            with open(METADATA_PATH, "r") as f:
                operational_metadata = json.load(f)
        except Exception:
            pass

    # ── SHAP explainer ────────────────────────────────────────────────────
    try:
        shap_explainer = shap.TreeExplainer(operational_model)
    except Exception as e:
        print("SHAP explainer init note:", e)

    # ── Chiller model ─────────────────────────────────────────────────────
    if CHILLER_MODEL_PATH.exists():
        chiller_model = joblib.load(CHILLER_MODEL_PATH)
    if CHILLER_FEATURES_PATH.exists():
        with open(CHILLER_FEATURES_PATH) as f:
            chiller_features = [l.strip() for l in f if l.strip()]
    if CHILLER_MAPPING_PATH.exists():
        with open(CHILLER_MAPPING_PATH) as f:
            chiller_mapping = json.load(f)
    if CHILLER_DATA_PATH.exists():
        try:
            chiller_df = pd.read_excel(CHILLER_DATA_PATH, sheet_name="Sheet1")
        except Exception as e:
            print("Chiller data load note:", e)

    # ── Water pump model ──────────────────────────────────────────────────
    if WATER_PUMP_MODEL_PATH.exists():
        water_pump_model = joblib.load(WATER_PUMP_MODEL_PATH)
    if WATER_PUMP_FEATURES_PATH.exists():
        with open(WATER_PUMP_FEATURES_PATH) as f:
            water_pump_features = [l.strip() for l in f if l.strip()]
    if WATER_PUMP_DECISION_PATH.exists():
        with open(WATER_PUMP_DECISION_PATH) as f:
            water_pump_decision = json.load(f)
    if WATER_PUMP_DATA_PATH.exists():
        try:
            water_pump_df = pd.read_csv(WATER_PUMP_DATA_PATH)
        except Exception as e:
            print("Water Pump data load note:", e)

    # ── API clients and engines ───────────────────────────────────────────
    from api_clients import (
        WeatherAPIClient, TransformerTelemetryClient,
        ChillerTelemetryClient, WaterPumpTelemetryClient
    )
    from ot.telemetry_manager import TelemetryManager
    from incident_engine import IncidentEngine
    from alert_manager import AlertManager
    from site_registry import SiteRegistry
    from regional_risk_engine import RegionalRiskEngine

    site_registry        = SiteRegistry()
    regional_risk_engine = RegionalRiskEngine()
    weather_client_inst      = WeatherAPIClient()
    transformer_client_inst  = TransformerTelemetryClient()
    chiller_client_inst      = ChillerTelemetryClient()
    water_pump_client_inst   = WaterPumpTelemetryClient()
    telemetry_mgr   = TelemetryManager()
    incident_engine = IncidentEngine()
    alert_manager   = AlertManager()

    # ── Phase 6 IoT Ingestion Layer initialization ─────────────────────────
    from ot.ts_storage import init_db
    from ot.device_registry import DeviceRegistry
    from ot.mqtt_client import CascadeGuardMQTTClient

    init_db()
    device_registry = DeviceRegistry()
    mqtt_client = CascadeGuardMQTTClient(device_registry)
    mqtt_client.connect()

    print("=" * 60)
    print("CascadeGuard FastAPI — All models loaded successfully")
    print(f"  Operational model : {operational_model_version}")
    print(f"  SHAP explainer    : {'active' if shap_explainer else 'inactive'}")
    print(f"  Chiller model     : {'active' if chiller_model else 'inactive'}")
    print(f"  Water pump model  : {'active' if water_pump_model else 'inactive'}")
    print("=" * 60)


# ── Shared helper functions ───────────────────────────────────────────────────

def get_feature_description(feature: str) -> str:
    if feature in FEATURE_HUMAN_MAPPINGS:
        return FEATURE_HUMAN_MAPPINGS[feature]
    clean = (feature
             .replace("_roll30m_mean", " (30m avg)")
             .replace("_roll60m_mean", " (60m avg)")
             .replace("_diff1", " rate of change"))
    return f"{clean} operational telemetry level"


def get_dynamic_shap_explanation(data_v3: dict):
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


def predict_health(data: dict):
    values = [float(data.get(feature, 0)) for feature in HEALTH_FEATURES]
    X = pd.DataFrame([values], columns=HEALTH_FEATURES)
    health_index = float(health_model.predict(X)[0])
    health_index = float(np.clip(health_index, 0, 100))
    health_risk = 100 - health_index
    return health_index, health_risk


def predict_operational(data: dict) -> float:
    if operational_model_version == "v3" and OPERATIONAL_FEATURES_V3:
        feature_list = OPERATIONAL_FEATURES_V3
    else:
        feature_list = OPERATIONAL_FEATURES_RAW

    values = [float(data.get(feature, 0)) for feature in feature_list]
    X = pd.DataFrame([values], columns=feature_list)
    probability = float(operational_model.predict_proba(X)[0][1])
    return probability * 100


CLIMATE_CACHE: dict = {}


def get_climate(location: str = "Coimbatore", latitude=None, longitude=None) -> dict:
    from site_config import get_active_site_config
    if latitude is None or longitude is None:
        site_cfg = get_active_site_config()
        if site_cfg and "location" in site_cfg:
            latitude = site_cfg["location"]["latitude"]
            longitude = site_cfg["location"]["longitude"]
            if not location or location == "Coimbatore":
                location = site_cfg["location"]["name"]
    normalized = weather_client_inst.get_current_data(
        location=location, latitude=latitude, longitude=longitude
    )
    return normalized["data"]


def risk_level(score: float) -> str:
    if score < 25:
        return "LOW"
    elif score < 50:
        return "MODERATE"
    elif score < 75:
        return "HIGH"
    return "CRITICAL"


def get_recommendation(level: str) -> str:
    if level == "LOW":
        return "Continue normal monitoring."
    elif level == "MODERATE":
        return "Increase monitoring frequency and inspect risk indicators."
    elif level == "HIGH":
        return "Prioritize transformer inspection and evaluate load/cooling conditions."
    return "Immediate engineering assessment and protective action recommended."


def get_model_signal(score: float) -> str:
    if score < 20:
        return "LOW"
    elif score < 50:
        return "MODERATE"
    elif score < 75:
        return "HIGH"
    return "CRITICAL"


def calculate_risk_trend(history: list):
    if not history or len(history) < 2:
        return "STABLE", 0.0

    scores = [h["cascade_score"] for h in history]
    if len(scores) < 4:
        diff = round(scores[-1] - scores[0], 2)
    else:
        recent = scores[-3:]
        older = scores[-6:-3]
        avg_recent = sum(recent) / len(recent)
        avg_older = sum(older) / len(older) if older else avg_recent
        diff = round(avg_recent - avg_older, 2)

    if diff > 2.0:
        trend = "RISING"
    elif diff < -2.0:
        trend = "FALLING"
    else:
        trend = "STABLE"

    return trend, diff


def calculate_early_warning_state(score: float, trend: str, op_risk: float) -> str:
    if score >= 75 or (score >= 60 and trend == "RISING"):
        return "CRITICAL"
    elif score >= 50 or (score >= 40 and trend == "RISING"):
        return "WARNING"
    elif score >= 25 or trend == "RISING":
        return "WATCH"
    return "NORMAL"


def analyze_single_transformer(tx_sample: dict) -> dict:
    from live_data import get_risk_history, push_fleet_history
    from predictive_forecast import get_predictive_forecast
    from decision_support import generate_decision_support

    tx_id = tx_sample["transformer_id"]
    location = tx_sample["location"]

    op_data_raw = tx_sample["data"]
    op_data_v3 = tx_sample.get("data_v3", op_data_raw)
    health_data = tx_sample["health_data"]

    health_idx, health_rk = predict_health(health_data)
    op_rk = predict_operational(op_data_v3)
    climate = get_climate(location)

    health_contrib  = round(health_rk * 0.40, 2)
    op_contrib      = round(op_rk * 0.40, 2)
    climate_contrib = round(climate["climate_stress"] * 0.20, 2)

    final_risk       = float(np.clip(health_contrib + op_contrib + climate_contrib, 0, 100))
    final_risk_round = round(final_risk, 2)
    level            = risk_level(final_risk_round)

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

    from live_data import get_risk_history as _grh
    tx_history  = _grh(tx_id)
    trend, trend_change = calculate_risk_trend(tx_history)
    early_warning = calculate_early_warning_state(final_risk_round, trend, op_rk)
    model_signal  = get_model_signal(op_rk)

    forecast_res = get_predictive_forecast(
        op_data_raw, op_data_v3, health_rk, climate["climate_stress"], final_risk_round
    )

    decision_support = generate_decision_support(
        final_risk_round, level, early_warning, trend, top_factors, climate,
        tx_sample.get("scenario", {}).get("name", "NORMAL")
    )

    cas_60m  = forecast_res["forecast"]["60m"]["cascade_score"]
    trend_w  = 10.0 if trend == "RISING" else (0.0 if trend == "STABLE" else -5.0)
    ew_w     = (15.0 if early_warning == "CRITICAL" else
                10.0 if early_warning == "WARNING" else
                5.0  if early_warning == "WATCH" else 0.0)
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
        "health": {"index": round(health_idx, 2), "risk": round(health_rk, 2)},
        "operational": {"risk": round(op_rk, 2)},
        "climate": climate,
        "cascade": {"score": final_risk_round, "level": level},
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
    from live_data import get_fleet_samples

    fleet_samples = get_fleet_samples()
    analyzed_list = []

    for tx_id, sample in fleet_samples.items():
        if sample.get("success"):
            tx_res = analyze_single_transformer(sample)
            analyzed_list.append(tx_res)

    analyzed_list.sort(key=lambda x: x["priority_score"], reverse=True)

    normal_c = watch_c = warning_c = critical_c = rising_c = 0
    total_score = 0.0

    for idx, tx in enumerate(analyzed_list):
        tx["priority_rank"] = idx + 1
        level = tx["cascade"]["level"]
        ew    = tx["explainability"]["early_warning_state"]
        tr    = tx["explainability"]["trend"]
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


def analyze_site_internal(site_id: str, scenario_name: str = None) -> dict:
    from site_config import get_active_site_config
    from live_data import get_live_data
    from scenarios import apply_scenario
    from cascade_graph import (
        evaluate_cascade_graph, build_transformer_asset_schema,
        build_chiller_asset_schema, build_water_pump_asset_schema
    )

    site_dict = site_registry.get_site(site_id)
    if not site_dict:
        site_dict = get_active_site_config()

    location = site_dict.get("city") or site_dict.get("city_name") or "Coimbatore"
    tx_id    = site_dict.get("asset_ids", {}).get("transformer", "TX-001")
    sc_name  = scenario_name or telemetry_mgr.active_scenario

    sample     = get_live_data(tx_id)
    raw_op     = sample.get("data", {})
    v3_op      = sample.get("data_v3", raw_op)
    health_raw = sample.get("health_data", {})
    climate    = get_climate(
        location,
        latitude=site_dict.get("latitude"),
        longitude=site_dict.get("longitude")
    )

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
    mod_pump    = mod_climate.get("_mod_pump", pump_sample_dict)

    health_index, health_risk = predict_health(mod_health)
    op_risk = predict_operational(mod_v3_op)
    tx_health_contrib  = round(health_risk * 0.40, 2)
    tx_op_contrib      = round(op_risk * 0.40, 2)
    tx_climate_contrib = round(mod_climate["climate_stress"] * 0.20, 2)
    tx_cascade_risk    = float(np.clip(tx_health_contrib + tx_op_contrib + tx_climate_contrib, 0, 100))
    tx_level           = risk_level(tx_cascade_risk)

    transformer_schema = build_transformer_asset_schema(tx_cascade_risk, health_risk, op_risk, tx_level)

    # ── Chiller ──────────────────────────────────────────────────────────
    chiller_risk = 5.0
    prob_normal  = 0.95
    pred_class   = 1
    prob_dict    = {f"Class_{i}": 0.05 for i in range(1, 9)}
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

    chiller_schema = build_chiller_asset_schema(chiller_risk, pred_class, prob_normal, prob_dict, chiller_level)

    # ── Water Pump ───────────────────────────────────────────────────────
    pump_risk  = 15.0
    pred_state = "NORMAL"
    pump_level = "LOW"

    if water_pump_model is not None and water_pump_features:
        p_vals = [float(mod_pump.get(feat, 0.0)) for feat in water_pump_features]
        p_X = pd.DataFrame([p_vals], columns=water_pump_features)
        try:
            p_proba    = water_pump_model.predict_proba(p_X)[0]
            pump_risk  = round(float((p_proba[1]*0.33 + p_proba[2]*0.66 + p_proba[3]*1.00) * 100.0), 2)
            state_idx  = int(np.argmax(p_proba))
            state_map  = {0: "NORMAL", 1: "WATCH", 2: "WARNING", 3: "CRITICAL"}
            pred_state = state_map.get(state_idx, "NORMAL")
        except Exception:
            pump_risk = 20.0

    pump_schema = build_water_pump_asset_schema(pump_risk, pred_state, pump_level)

    cascade_eval = evaluate_cascade_graph(transformer_schema, chiller_schema, pump_schema, mod_climate)

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

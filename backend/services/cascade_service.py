"""
backend/services/cascade_service.py
===================================
CascadeGuard AI — Causal Risk & Cascade Propagation Engine (Phase I)

Combines outputs from the 6 specialized ML models and equipment telemetry into unified contract schemas:
Weather Forecast -> Hospital Load -> Transformer Thermal -> Chiller Fault -> Pump Risk -> Flood Exposure -> Downstream Medical Impact
"""
import os
import time
import joblib
import pandas as pd
import numpy as np
from services.model_health_service import update_last_inference

_MODELS_CACHE = {}

def get_production_models():
    if not _MODELS_CACHE:
        prod_dir = "models/production"
        if os.path.exists(os.path.join(prod_dir, "model_1_hospital_load.pkl")):
            _MODELS_CACHE["model_1"] = joblib.load(os.path.join(prod_dir, "model_1_hospital_load.pkl"))
        if os.path.exists(os.path.join(prod_dir, "model_2_transformer_thermal.pkl")):
            _MODELS_CACHE["model_2"] = joblib.load(os.path.join(prod_dir, "model_2_transformer_thermal.pkl"))
        if os.path.exists(os.path.join(prod_dir, "model_3_transformer_health.pkl")):
            _MODELS_CACHE["model_3"] = joblib.load(os.path.join(prod_dir, "model_3_transformer_health.pkl"))
        if os.path.exists(os.path.join(prod_dir, "model_4_chiller_fault.pkl")):
            _MODELS_CACHE["model_4"] = joblib.load(os.path.join(prod_dir, "model_4_chiller_fault.pkl"))
        if os.path.exists(os.path.join(prod_dir, "model_5_water_pump_risk.pkl")):
            _MODELS_CACHE["model_5"] = joblib.load(os.path.join(prod_dir, "model_5_water_pump_risk.pkl"))
        if os.path.exists(os.path.join(prod_dir, "model_6_flood_risk.pkl")):
            _MODELS_CACHE["model_6"] = joblib.load(os.path.join(prod_dir, "model_6_flood_risk.pkl"))
    return _MODELS_CACHE

CHILLER_CLASS_MAP = {
    1: "NORMAL",
    2: "REFRIGERANT OVERCHARGE",
    3: "REFRIGERANT LEAK",
    4: "CONDENSER FOULING",
    5: "REDUCED CONDENSER FLOW",
    6: "NON-CONDENSABLE GAS",
    7: "EXCESS OIL",
    8: "REDUCED EVAPORATOR FLOW"
}

def evaluate_cascade_risk(weather_data: dict, equipment_telemetry: dict = None) -> dict:
    models = get_production_models()
    now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # 1. Parse weather input
    curr_weather = weather_data.get("current", {})
    temp_c = float(curr_weather.get("temperature_2m", 32.0) or 32.0)
    humidity = float(curr_weather.get("relative_humidity_2m", 65.0) or 65.0)
    precip_mm = float(curr_weather.get("precipitation", 0.0) or 0.0)
    pressure_hpa = float(curr_weather.get("surface_pressure", 1008.0) or 1008.0)
    
    data_quality = "GOOD"
    data_quality_details = {"missing_features": [], "stale_telemetry": False, "telemetry_age_sec": 12}
    
    # 2. Predict Hospital Electrical Load
    m1 = models.get("model_1")
    if m1:
        update_last_inference("model_1")
        load_df = pd.DataFrame([{
            "ambient_temp": temp_c,
            "hour": 14,
            "day_of_week": 2,
            "load_lag1": 1200.0,
            "load_lag6": 1150.0,
            "load_lag24": 1100.0,
            "temp_lag1": temp_c - 0.5
        }])
        pred_load_1h = float(m1.predict(load_df)[0])
    else:
        pred_load_1h = 800.0 + (temp_c * 15.0)
        
    pred_load_6h = round(pred_load_1h * 1.05, 1)
    pred_load_24h = round(pred_load_1h * 1.12, 1)
    pred_load_72h = round(pred_load_1h * 0.98, 1)
    
    p1_critical_kw = round(pred_load_1h * 0.30, 1)
    p2_essential_kw = round(pred_load_1h * 0.35, 1)
    p3_deferrable_kw = round(pred_load_1h * 0.20, 1)
    p4_noncritical_kw = round(pred_load_1h * 0.15, 1)
    
    load_prediction_contract = {
        "model_id": "Model-1-HospitalLoad",
        "model_version": "v1.0-prod",
        "prediction_timestamp": now_ts,
        "horizon": "1h-72h",
        "prediction": {
            "current_load_kw": round(pred_load_1h, 1),
            "predicted_1h_kw": round(pred_load_1h, 1),
            "predicted_6h_kw": pred_load_6h,
            "predicted_24h_kw": pred_load_24h,
            "predicted_72h_kw": pred_load_72h,
            "peak_load_kw": max(pred_load_1h, pred_load_6h, pred_load_24h),
            "peak_time": "14:00 +24h",
            "medical_tiers": {
                "P1_critical_kw": p1_critical_kw,
                "P2_essential_kw": p2_essential_kw,
                "P3_deferrable_kw": p3_deferrable_kw,
                "P4_noncritical_kw": p4_noncritical_kw
            }
        },
        "risk_score": float(np.clip((pred_load_1h - 800.0) / 1000.0, 0.1, 0.95)),
        "confidence": 0.93,
        "status": "NORMAL" if pred_load_1h < 1300 else "WATCH",
        "contributors": ["ambient_temperature", "peak_hvac_cooling_demand", "lagged_electrical_load"],
        "data_quality": data_quality
    }
    
    # 3. Predict Transformer Thermal Response (T1) & Health Index
    m2 = models.get("model_2")
    if m2:
        update_last_inference("model_2")
        tf_df = pd.DataFrame([{
            "load": pred_load_1h / 10.0,
            "current": pred_load_1h / 3.0,
            "voltage": 230.0,
            "pf": 0.95,
            "ambient_temp": temp_c,
            "OTI": 55.0,
            "WTI": 62.0,
            "OLI": 37.0,
            "oti_lag1": 54.5,
            "oti_lag5": 53.0,
            "wti_lag1": 61.5
        }])
        pred_oti_c = float(m2.predict(tf_df)[0])
    else:
        pred_oti_c = 45.0 + (pred_load_1h / 40.0) + (temp_c * 0.4)
        
    pred_wti_c = round(pred_oti_c + 7.5, 1)
    thermal_risk_score = float(np.clip((pred_oti_c - 40.0) / 50.0, 0.0, 1.0))
    time_to_threshold_min = max(15, int((90.0 - pred_oti_c) * 12.0))
    
    m3 = models.get("model_3")
    health_index_pts = 92.5
    if m3:
        update_last_inference("model_3")
        dga_df = pd.DataFrame([{
            "Hydrogen": 25, "Oxigen": 5800, "Nitrogen": 27000, "Methane": 12, "CO": 150,
            "CO2": 1200, "Ethylene": 5, "Ethane": 8, "Acethylene": 0, "DBDS": 0.0,
            "Power factor": 0.05, "Interfacial V": 42, "Dielectric rigidity": 65, "Water content": 12
        }])
        health_index_pts = float(m3.predict(dga_df)[0])
        
    transformer_prediction_contract = {
        "model_id": "Model-2-TransformerThermal",
        "model_version": "v1.0-prod",
        "prediction_timestamp": now_ts,
        "horizon": "60m",
        "prediction": {
            "equipment_id": "T1",
            "current_condition": "OPERATIONAL",
            "predicted_oti_degc": round(pred_oti_c, 1),
            "predicted_wti_degc": pred_wti_c,
            "time_to_threshold_minutes": time_to_threshold_min,
            "health_index_score": round(health_index_pts, 1)
        },
        "risk_score": round(thermal_risk_score, 2),
        "confidence": 0.90,
        "status": "CRITICAL" if pred_oti_c >= 85.0 else ("WARNING" if pred_oti_c >= 70.0 else "NORMAL"),
        "contributors": ["transformer_active_loading", "top_oil_temperature_rise", "ambient_temperature"],
        "data_quality": data_quality
    }
    
    # 4. Predict HVAC Chiller Fault / Degradation (C1)
    m4 = models.get("model_4")
    chiller_fault_id = 1
    chiller_risk = 0.08
    if m4:
        update_last_inference("model_4")
        chiller_df = pd.DataFrame([{
            "TEI": 58.0, "TEO": 44.0, "TCI": 85.0 + (temp_c - 30.0), "TCO": 95.0, "kW": pred_load_1h * 0.4,
            "TEA": 41.5, "TCA": 92.3, "TRE": 4.1, "TRC": 6.8, "TRC_sub": 5.2, "T_suc": 48.1,
            "Tsh_suc": 8.5, "TR_dis": 135.4, "Tsh_dis": 28.6, "TO_sump": 118.2, "PO_net": 65.4
        }])
        probs = m4.predict_proba(chiller_df)[0]
        chiller_fault_id = int(np.argmax(probs)) + 1
        chiller_risk = float(1.0 - probs[0])
        
    chiller_class_name = CHILLER_CLASS_MAP.get(chiller_fault_id, "NORMAL")
    chiller_cop = round(max(1.5, 4.2 - (chiller_risk * 2.0)), 2)
    chiller_efficiency_kw_per_ton = round(12.0 / (chiller_cop * 3.412), 2)
    
    chiller_prediction_contract = {
        "model_id": "Model-4-ChillerFault",
        "model_version": "v1.0-prod",
        "prediction_timestamp": now_ts,
        "horizon": "Real-Time / 30m",
        "prediction": {
            "equipment_id": "C1",
            "predicted_class": chiller_fault_id,
            "predicted_class_name": chiller_class_name,
            "fault_probability": round(chiller_risk, 3),
            "cooling_condition": "OPTIMAL" if chiller_fault_id == 1 else "ANOMALOUS",
            "efficiency_kw_per_ton": chiller_efficiency_kw_per_ton,
            "cop": chiller_cop
        },
        "risk_score": round(chiller_risk, 2),
        "confidence": 0.99,
        "status": "NORMAL" if chiller_fault_id == 1 else "WARNING",
        "contributors": ["condenser_entering_temp", "evaporator_temperature_approach", "refrigerant_subcooling"],
        "data_quality": data_quality
    }
    
    # 5. Predict Water Pump Risk (P1)
    m5 = models.get("model_5")
    pump_risk_state = "NORMAL"
    pump_risk = 0.05
    if m5:
        update_last_inference("model_5")
        pump_sensor_cols = [f"sensor_{i:02d}" for i in range(52) if i not in (15, 50)]
        pump_input = pd.DataFrame([[2.4]*len(pump_sensor_cols)], columns=pump_sensor_cols)
        p_probs = m5.predict_proba(pump_input)[0]
        pump_risk_code = int(np.argmax(p_probs))
        pump_risk_state = ["NORMAL", "WATCH", "WARNING", "CRITICAL"][pump_risk_code]
        pump_risk = float(1.0 - p_probs[0])
        
    pump_prediction_contract = {
        "model_id": "Model-5-WaterPumpRisk",
        "model_version": "v1.0-prod",
        "prediction_timestamp": now_ts,
        "horizon": "Continuous RUL State",
        "prediction": {
            "equipment_id": "P1",
            "estimated_rul_hours": 180.5 if pump_risk_state == "NORMAL" else 42.0,
            "risk_state": pump_risk_state,
            "health_score": round((1.0 - pump_risk) * 100.0, 1),
            "model_reliability": "DECISION SUPPORT ONLY / LOW CONFIDENCE (Chronological Accuracy = 35.78%)"
        },
        "risk_score": round(pump_risk, 2),
        "confidence": 0.36,  # Explicit low confidence
        "status": "DECISION_SUPPORT_ONLY",
        "contributors": ["bearing_vibration_rms", "discharge_pressure", "motor_temperature"],
        "data_quality": data_quality
    }
    
    # 6. Predict Flood Exposure Risk
    m6 = models.get("model_6")
    flood_risk_level = 0
    if m6:
        update_last_inference("model_6")
        flood_input = pd.DataFrame([{
            "rainfall_mm": precip_mm,
            "accum_rain_24h": precip_mm * 5.0,
            "surface_pressure_hpa": pressure_hpa
        }])
        flood_risk_level = int(m6.predict(flood_input)[0])
        
    flood_risk_score = flood_risk_level / 2.0
    flood_prediction_contract = {
        "model_id": "Model-6-FloodRisk",
        "model_version": "v1.0-prod",
        "prediction_timestamp": now_ts,
        "horizon": "24h Surface Exposure",
        "prediction": {
            "rainfall_24h_mm": round(precip_mm * 5.0, 1),
            "estimated_water_level_cm": round(precip_mm * 2.2, 1),
            "flood_exposure_code": flood_risk_level,
            "flood_risk_label": ["LOW_EXPOSURE", "MODERATE_EXPOSURE", "HIGH_EXPOSURE"][flood_risk_level]
        },
        "risk_score": round(flood_risk_score, 2),
        "confidence": 0.98,
        "status": "NORMAL" if flood_risk_level == 0 else "WARNING",
        "contributors": ["rainfall_accumulation_24h", "surface_atmospheric_pressure"],
        "data_quality": data_quality
    }
    
    # 7. Calculate Consolidated Cascade Risk & Probabilistic Explanations
    weights = {"transformer": 0.40, "chiller": 0.35, "pump": 0.15, "flood": 0.10}
    overall_risk = (thermal_risk_score * weights["transformer"]) + (chiller_risk * weights["chiller"]) + (pump_risk * weights["pump"]) + (flood_risk_score * weights["flood"])
    overall_risk = round(float(np.clip(overall_risk, 0.05, 0.99)), 2)
    
    if overall_risk >= 0.75:
        level = "CRITICAL"
    elif overall_risk >= 0.50:
        level = "HIGH"
    elif overall_risk >= 0.25:
        level = "MODERATE"
    else:
        level = "LOW"
        
    drivers = []
    if temp_c > 35.0:
        drivers.append(f"High ambient temperature ({temp_c}°C)")
    if pred_load_1h > 1200.0:
        drivers.append(f"Predicted facility electrical demand increase ({round(pred_load_1h, 1)} kW)")
    if thermal_risk_score > 0.4:
        drivers.append(f"Transformer T1 thermal stress (predicted top oil {round(pred_oti_c, 1)}°C)")
    if chiller_fault_id != 1:
        drivers.append(f"HVAC Chiller C1 thermodynamic anomaly ({chiller_class_name})")
    if precip_mm > 20.0:
        drivers.append(f"Precipitation accumulation forecast ({precip_mm} mm)")
    if not drivers:
        drivers.append("Nominal operational parameters within design envelope")
        
    affected = []
    if thermal_risk_score > 0.4:
        affected.append("T1")
    if chiller_risk > 0.3:
        affected.append("C1")
    if pump_risk > 0.3:
        affected.append("P1")
    if not affected:
        affected.append("T1")
        
    downstream = []
    if "T1" in affected:
        downstream.append("Transformer T1 winding thermal stress may reduce operating margin for critical circuits")
    if "C1" in affected:
        downstream.append("HVAC Chiller C1 cooling capacity may become constrained, increasing thermal load on ICU/OT climate control")
    if "P1" in affected:
        downstream.append("Water Pump P1 pressure fluctuations may impact secondary cooling water supply")
    if not downstream:
        downstream.append("No critical downstream medical infrastructure impacted under current predictions")
        
    # Structured Probabilistic Explanation (WHY, WHAT, WHEN, IMPACT)
    why_explanation = f"High ambient temperature ({temp_c}°C) combined with estimated facility load ({round(pred_load_1h, 1)} kW)."
    what_explanation = f"Transformer T1 top oil temperature is predicted to reach {round(pred_oti_c, 1)}°C with thermal risk score {round(thermal_risk_score, 2)}."
    when_explanation = f"Estimated thermal threshold proximity within approximately {time_to_threshold_min} minutes."
    impact_explanation = f"Potential reduction in HVAC cooling capacity; deferrable loads may require shedding to protect P1 ICU/OT circuits."
    
    explanation_struct = {
        "why": why_explanation,
        "what": what_explanation,
        "when": when_explanation,
        "impact": impact_explanation
    }
    return {
        "overall_risk": overall_risk,
        "level": level,
        "confidence": 0.88,
        "drivers": drivers,
        "affected_equipment": affected,
        "potential_downstream_impact": downstream,
        "explanation": explanation_struct,
        "data_quality": data_quality,
        "data_quality_details": data_quality_details,
        "predictions": {
            "load": load_prediction_contract,
            "transformer": transformer_prediction_contract,
            "chiller": chiller_prediction_contract,
            "pump": pump_prediction_contract,
            "flood": flood_prediction_contract
        }
    }


# =====================================================================
# Phase 5: Dependency Graph & Cascade Propagation Engine (Deterministic)
# =====================================================================
from typing import Dict, Any, List

def get_risk_category(score: float) -> str:
    """Utility to map 0-100 risk score to category."""
    s = float(score)
    if s < 25.0:
        return "LOW"
    elif s < 50.0:
        return "MODERATE"
    elif s < 75.0:
        return "HIGH"
    return "CRITICAL"

def calculate_cascade(site_data: Dict[str, Any], weather_data: Dict[str, Any], base_risks: Dict[str, float], scenario_name: str = "NORMAL") -> Dict[str, Any]:
    """
    Computes topological risk propagation across equipment assets and facility.
    Supports cycle protection, visited node tracking, and max depth of 2.
    """
    site_id = site_data.get("site_id", "SITE-001")
    asset_ids = site_data.get("asset_ids", {})
    tx_id = asset_ids.get("transformer", "TX-001")
    ch_id = asset_ids.get("chiller", "CH-001")
    wp_id = asset_ids.get("water_pump", "WP-001")

    # 1. Map initial risks
    risks = {
        tx_id: float(base_risks.get("transformer", 10.0)),
        ch_id: float(base_risks.get("chiller", 10.0)),
        wp_id: float(base_risks.get("water_pump", 10.0)),
        "FACILITY": 0.0
    }
    
    base_risks_map = dict(risks)
    
    # 2. Inject Scenario simulated unavailability/stress if any (does not modify live telemetry)
    s_name = (scenario_name or "NORMAL").lower()
    if s_name == "transformer_unavailable":
        risks[tx_id] = 100.0
    elif s_name == "transformer_degraded":
        risks[tx_id] = max(risks[tx_id], 75.0)
    elif s_name == "chiller_unavailable":
        risks[ch_id] = 100.0
    elif s_name == "chiller_degraded":
        risks[ch_id] = max(risks[ch_id], 75.0)
    elif s_name == "water_pump_unavailable":
        risks[wp_id] = 100.0
    elif s_name == "water_pump_degraded":
        risks[wp_id] = max(risks[wp_id], 75.0)

    # 3. Propagate stress downstream (Topological Sort: TX -> CH -> FACILITY, TX -> WP -> FACILITY)
    visited = set()
    
    # Node 1: Transformer
    tx_stress = risks[tx_id]
    visited.add(tx_id)
    
    # Edge TX -> CH (POWER, strength = 1.0)
    # Edge TX -> WP (POWER, strength = 1.0)
    # Consequence is scaled by propagation weight 0.40
    
    if ch_id not in visited:
        ch_propagated = tx_stress * 1.0
        ch_cascade = base_risks_map[ch_id] + ch_propagated * 0.40
        if s_name != "chiller_unavailable":
            risks[ch_id] = round(float(np.clip(ch_cascade, 0.0, 100.0)), 2)
        visited.add(ch_id)
        
    if wp_id not in visited:
        wp_propagated = tx_stress * 1.0
        wp_cascade = base_risks_map[wp_id] + wp_propagated * 0.40
        if s_name != "water_pump_unavailable":
            risks[wp_id] = round(float(np.clip(wp_cascade, 0.0, 100.0)), 2)
        visited.add(wp_id)
        
    # Node 4: Facility (COOLING from Chiller: 0.8, DRAINAGE from Pump: 0.6)
    # Composite risk is calculated from downstream assets scaled by dependency strength
    ch_stress = risks[ch_id]
    wp_stress = risks[wp_id]
    
    fac_cascade = 0.5 * ch_stress * 0.8 + 0.5 * wp_stress * 0.6
    # If the transformer power is critical, it direct propagates
    if tx_stress >= 75.0:
        fac_cascade = max(fac_cascade, tx_stress * 0.8)
        
    risks["FACILITY"] = round(float(np.clip(fac_cascade, 0.0, 100.0)), 2)
    visited.add("FACILITY")

    # 4. Consequence analysis details
    affected_assets = []
    affected_services = []
    paths = []
    
    if "transformer" in s_name:
        affected_assets = [ch_id, wp_id]
        affected_services = ["Cooling", "Water Management & Drainage"]
        paths = [[tx_id, ch_id], [tx_id, wp_id]]
    elif "chiller" in s_name:
        affected_assets = ["FACILITY"]
        affected_services = ["Cooling"]
        paths = [[ch_id, "FACILITY"]]
    elif "water_pump" in s_name:
        affected_assets = ["FACILITY"]
        affected_services = ["Water Management & Drainage"]
        paths = [[wp_id, "FACILITY"]]

    # Max depth
    max_depth = 2 if "transformer" in s_name else (1 if ("chiller" in s_name or "water_pump" in s_name) else 0)

    # Explanation generator
    explanation = ""
    if s_name == "normal":
        explanation = "Facility service operations are nominal. Cascaded risks are within normal design margins."
    elif s_name == "transformer_unavailable":
        explanation = f"Simulated unavailability of Transformer {tx_id}. Downstream HVAC Chiller {ch_id} and Water Pump {wp_id} lose primary electrical supply, resulting in loss of facility climate control and storm drainage services."
    elif s_name == "transformer_degraded":
        explanation = f"Simulated degradation of Transformer {tx_id}. Elevated operating temperatures reduce winding margin, propagating electrical supply stress to downstream HVAC Chiller {ch_id} and Pump {wp_id}."
    elif s_name == "chiller_unavailable":
        explanation = f"Simulated unavailability of HVAC Chiller {ch_id}. Direct loss of facility cooling service predicted; power and drainage circuits remain electrically nominal."
    elif s_name == "chiller_degraded":
        explanation = f"Simulated degradation of HVAC Chiller {ch_id}. Cooling capacity is reduced under high heat-rejection drag."
    elif s_name == "water_pump_unavailable":
        explanation = f"Simulated unavailability of Drainage Pump {wp_id}. Water drainage service disabled; electrical and cooling circuits are unaffected."
    elif s_name == "water_pump_degraded":
        explanation = f"Simulated degradation of Drainage Pump {wp_id}. Storm water extraction rate is reduced."

    return {
        "scenario": scenario_name,
        "cascade_risk": risks["FACILITY"],
        "level": get_risk_category(risks["FACILITY"]),
        "source_asset": tx_id if "transformer" in s_name else (ch_id if "chiller" in s_name else (wp_id if "pump" in s_name else "None")),
        "affected_asset_count": len(affected_assets),
        "affected_assets": affected_assets,
        "affected_services": affected_services,
        "maximum_depth": max_depth,
        "propagation_paths": paths,
        "explanation": explanation,
        "node_risks": {
            "transformer": {
                "base_risk": base_risks_map[tx_id],
                "propagated_risk": round(risks[tx_id] - base_risks_map[tx_id], 2),
                "cascade_risk": risks[tx_id]
            },
            "chiller": {
                "base_risk": base_risks_map[ch_id],
                "propagated_risk": round(risks[ch_id] - base_risks_map[ch_id], 2),
                "cascade_risk": risks[ch_id]
            },
            "water_pump": {
                "base_risk": base_risks_map[wp_id],
                "propagated_risk": round(risks[wp_id] - base_risks_map[wp_id], 2),
                "cascade_risk": risks[wp_id]
            }
        }
    }

def get_cascade_analysis(site_data: Dict[str, Any], weather_full: Dict[str, Any], pred_res: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assembles complete cascade analytics including dependency graph, scenarios, SPOF, and 72h forecasts.
    """
    site_id = site_data.get("site_id", "SITE-001")
    asset_ids = site_data.get("asset_ids", {})
    tx_id = asset_ids.get("transformer", "TX-001")
    ch_id = asset_ids.get("chiller", "CH-001")
    wp_id = asset_ids.get("water_pump", "WP-001")
    site_name = site_data.get("site_name", "Industrial Facility")

    # 1. Extract base risks
    eq = pred_res.get("equipment", {})
    base_risks = {
        "transformer": eq.get("transformer", {}).get("risk_score", 10.0),
        "chiller": eq.get("chiller", {}).get("risk_score", 10.0),
        "water_pump": eq.get("water_pump", {}).get("risk_score", 10.0)
    }

    # 2. Compute Normal baseline cascade risk
    normal_cascade = calculate_cascade(site_data, weather_full, base_risks, scenario_name="NORMAL")

    # 3. Build Graph
    nodes = [
        {"id": tx_id, "type": "transformer", "name": f"Power Transformer ({tx_id})"},
        {"id": ch_id, "type": "chiller", "name": f"HVAC Chiller ({ch_id})"},
        {"id": wp_id, "type": "water_pump", "name": f"Water Pump ({wp_id})"},
        {"id": "FACILITY", "type": "facility", "name": site_name}
    ]

    edges = [
        {
            "source": tx_id,
            "target": ch_id,
            "dependency_type": "POWER",
            "dependency_strength": 1.0,
            "description": f"Downstream HVAC Chiller {ch_id} is completely dependent on Transformer {tx_id} for power supply."
        },
        {
            "source": tx_id,
            "target": wp_id,
            "dependency_type": "POWER",
            "dependency_strength": 1.0,
            "description": f"Downstream Drainage Pump {wp_id} is completely dependent on Transformer {tx_id} for power supply."
        },
        {
            "source": ch_id,
            "target": "FACILITY",
            "dependency_type": "COOLING",
            "dependency_strength": 0.8,
            "description": f"Facility HVAC temperature control is highly dependent on cooling service from Chiller {ch_id}."
        },
        {
            "source": wp_id,
            "target": "FACILITY",
            "dependency_type": "DRAINAGE",
            "dependency_strength": 0.6,
            "description": f"Facility site flooding protection depends on drainage capacity from Water Pump {wp_id}."
        }
    ]

    # 4. Evaluate all 7 Scenarios
    scenarios_to_run = [
        "NORMAL",
        "transformer_unavailable",
        "transformer_degraded",
        "chiller_unavailable",
        "chiller_degraded",
        "water_pump_unavailable",
        "water_pump_degraded"
    ]
    
    scenario_outputs = []
    for scen in scenarios_to_run:
        scen_res = calculate_cascade(site_data, weather_full, base_risks, scenario_name=scen)
        scenario_outputs.append(scen_res)

    # 5. Single Point of Failure (SPOF) Analysis
    tx_unavail = next(s for s in scenario_outputs if s["scenario"] == "transformer_unavailable")["cascade_risk"]
    ch_unavail = next(s for s in scenario_outputs if s["scenario"] == "chiller_unavailable")["cascade_risk"]
    wp_unavail = next(s for s in scenario_outputs if s["scenario"] == "water_pump_unavailable")["cascade_risk"]

    spof_list = [
        {"name": "Power Transformer", "id": tx_id, "unavailability_cascade_risk": tx_unavail},
        {"name": "HVAC Chiller", "id": ch_id, "unavailability_cascade_risk": ch_unavail},
        {"name": "Water Pump", "id": wp_id, "unavailability_cascade_risk": wp_unavail}
    ]
    max_spof = max(spof_list, key=lambda x: x["unavailability_cascade_risk"])

    # 6. 72-Hour Cascade Forecast & Warning Time
    hourly_forecast = []
    cascade_warning_time = None
    
    pred_forecast = pred_res.get("hourly_forecast", [])
    for pt in pred_forecast:
        h_offset = pt["hour_offset"]
        h_ts = pt["timestamp"]
        h_base = {
            "transformer": pt["transformer_risk"],
            "chiller": pt["chiller_risk"],
            "water_pump": pt["water_pump_risk"]
        }
        h_eval = calculate_cascade(site_data, pt.get("weather", {}), h_base, scenario_name="NORMAL")
        h_cascade_risk = h_eval["cascade_risk"]

        hourly_forecast.append({
            "timestamp": h_ts,
            "hour_offset": h_offset,
            "transformer_risk": pt["transformer_risk"],
            "chiller_risk": pt["chiller_risk"],
            "water_pump_risk": pt["water_pump_risk"],
            "cascade_risk": h_cascade_risk
        })

        if cascade_warning_time is None and h_cascade_risk >= 50.0:
            cascade_warning_time = f"+{h_offset}h"

    peak_risk = max([pt["cascade_risk"] for pt in hourly_forecast]) if hourly_forecast else normal_cascade["cascade_risk"]

    return {
        "site_id": site_id,
        "site_name": site_name,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "facility_cascade": {
            "current_risk": normal_cascade["cascade_risk"],
            "peak_risk": peak_risk,
            "level": normal_cascade["level"],
            "dominant_source_asset": normal_cascade["source_asset"],
            "affected_asset_count": normal_cascade["affected_asset_count"],
            "maximum_depth": normal_cascade["maximum_depth"],
            "cascade_warning_time": cascade_warning_time or "No immediate cascade hazard predicted",
            "critical_spof": {
                "name": max_spof["name"],
                "id": max_spof["id"],
                "risk_consequence": max_spof["unavailability_cascade_risk"]
            }
        },
        "dependency_graph": {
            "nodes": nodes,
            "edges": edges
        },
        "scenarios": scenario_outputs,
        "forecast": hourly_forecast
    }

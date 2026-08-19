"""
backend/services/recommendation_service.py
=========================================
CascadeGuard AI — AI Recommendation & Ollama Advisories Engine (Phase F)

Uses predefined Action Library and optional Ollama LLM integration to generate
structured facility operator recommendations with mandatory human approval flags.
"""
import os
import json
import requests

ACTION_LIBRARY = {
    "ACTIVATE_COOLING": {
        "action": "ACTIVATE_COOLING",
        "reason": "High ambient temperature and transformer top oil temperature approaching thermal threshold.",
        "expected_effect": "Reduces transformer oil temperature by 5–8°C within 30 minutes.",
        "priority": "HIGH",
        "requires_human_approval": True
    },
    "SHIFT_NONCRITICAL_LOAD": {
        "action": "SHIFT_NONCRITICAL_LOAD",
        "reason": "Facility electrical load exceeding 85% transformer capacity; risk of thermal overload.",
        "expected_effect": "Sheds 15–20% load from P4 non-critical circuits (Admin HVAC, decorative lighting).",
        "priority": "CRITICAL",
        "requires_human_approval": True
    },
    "OPTIMIZE_CHILLER": {
        "action": "OPTIMIZE_CHILLER",
        "reason": "HVAC Chiller C1 exhibiting thermodynamic approach anomaly or reduced COP efficiency.",
        "expected_effect": "Restores COP efficiency and stabilizes chilled water supply temperature to ICU/OT.",
        "priority": "HIGH",
        "requires_human_approval": True
    },
    "INSPECT_COOLING_SYSTEM": {
        "action": "INSPECT_COOLING_SYSTEM",
        "reason": "Transformer oil temperature indicator (OTI) rising rapidly relative to ambient.",
        "expected_effect": "Identifies fan failure or radiator obstruction before thermal trip.",
        "priority": "MEDIUM",
        "requires_human_approval": True
    },
    "CHECK_OIL_LEVEL": {
        "action": "CHECK_OIL_LEVEL",
        "reason": "Transformer Oil Level Indicator (OLI) or Sump Oil Pressure reading outside nominal range.",
        "expected_effect": "Prevents dielectric breakdown and mechanical seal damage.",
        "priority": "HIGH",
        "requires_human_approval": True
    },
    "PREPARE_BACKUP_SUPPLY": {
        "action": "PREPARE_BACKUP_SUPPLY",
        "reason": "Overall cascade risk score in CRITICAL zone (>0.75).",
        "expected_effect": "Ensures DG set readiness and uninterrupted power to P1 critical medical tiers.",
        "priority": "CRITICAL",
        "requires_human_approval": True
    },
    "CHECK_DRAINAGE": {
        "action": "CHECK_DRAINAGE",
        "reason": "Precipitation accumulation forecast indicating surface water accumulation risk.",
        "expected_effect": "Prevents basement pump room inundation.",
        "priority": "MEDIUM",
        "requires_human_approval": True
    },
    "PREPARE_FLOOD_BARRIERS": {
        "action": "PREPARE_FLOOD_BARRIERS",
        "reason": "Heavy rainfall forecast with high surface water level exposure code.",
        "expected_effect": "Protects ground-level transformer substation from water ingress.",
        "priority": "HIGH",
        "requires_human_approval": True
    },
    "INSPECT_PUMP": {
        "action": "INSPECT_PUMP",
        "reason": "Water Pump P1 risk state classified as WARNING or CRITICAL.",
        "expected_effect": "Prevents catastrophic pump cavitation or bearing failure.",
        "priority": "HIGH",
        "requires_human_approval": True
    }
}

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

def generate_recommendations(cascade_result: dict) -> dict:
    overall_risk = cascade_result.get("overall_risk", 0.1)
    affected = cascade_result.get("affected_equipment", ["T1"])
    preds = cascade_result.get("predictions", {})
    
    actions = []
    
    # Deterministic Action Selection from Action Library
    if overall_risk >= 0.75:
        a = dict(ACTION_LIBRARY["PREPARE_BACKUP_SUPPLY"])
        a["affected_equipment"] = ["T1", "C1", "P1"]
        actions.append(a)
        
        a2 = dict(ACTION_LIBRARY["SHIFT_NONCRITICAL_LOAD"])
        a2["affected_equipment"] = ["T1"]
        a2["reason"] += f" Predicted load: {preds.get('hospital_total_load_kw', 1200)} kW."
        actions.append(a2)
        
    if preds.get("transformer_predicted_oti_c", 45.0) > 65.0 or "T1" in affected:
        a = dict(ACTION_LIBRARY["ACTIVATE_COOLING"])
        a["affected_equipment"] = ["T1"]
        a["reason"] += f" Predicted top oil temp: {preds.get('transformer_predicted_oti_c', 65.0)}°C."
        actions.append(a)
        
    if preds.get("chiller_degradation_risk", 0.0) > 0.3 or "C1" in affected:
        a = dict(ACTION_LIBRARY["OPTIMIZE_CHILLER"])
        a["affected_equipment"] = ["C1"]
        actions.append(a)
        
    if preds.get("pump_risk_state") in ["WARNING", "CRITICAL"] or "P1" in affected:
        a = dict(ACTION_LIBRARY["INSPECT_PUMP"])
        a["affected_equipment"] = ["P1"]
        a["reason"] += f" Current pump state: {preds.get('pump_risk_state', 'WARNING')}."
        actions.append(a)
        
    if preds.get("flood_exposure_code", 0) > 0:
        a = dict(ACTION_LIBRARY["PREPARE_FLOOD_BARRIERS"])
        a["affected_equipment"] = ["CLIMATE-01"]
        actions.append(a)
        
    if not actions:
        a = dict(ACTION_LIBRARY["INSPECT_COOLING_SYSTEM"])
        a["affected_equipment"] = ["T1"]
        a["priority"] = "LOW"
        actions.append(a)
        
    # Ollama Natural Language Summary (with fallback if Ollama is not running)
    ollama_explanation = _query_ollama_explanation(cascade_result, actions)
    
    return {
        "facility": "KMCH",
        "city": "Coimbatore",
        "overall_risk": overall_risk,
        "level": cascade_result.get("level", "LOW"),
        "actions": actions,
        "ai_explanation": ollama_explanation,
        "source": "CascadeGuard Rules & Ollama Reasoning Engine"
    }

def _query_ollama_explanation(cascade_result: dict, actions: list) -> str:
    prompt = f"""You are the CascadeGuard AI Facility Operator Advisory System.
Given the following verified ML risk metrics for KMCH Hospital infrastructure:
Overall Risk: {cascade_result.get('overall_risk')} ({cascade_result.get('level')})
Drivers: {', '.join(cascade_result.get('drivers', []))}
Affected Equipment: {', '.join(cascade_result.get('affected_equipment', []))}
Downstream Impact: {', '.join(cascade_result.get('potential_downstream_impact', []))}

Recommended Operator Actions:
{json.dumps([a['action'] for a in actions])}

Provide a concise, professional, 3-sentence advisory for the facility engineer explaining why this risk is happening, the predicted consequence, and why human approval is required for the recommended actions. Do not invent fake sensor numbers.
"""
    try:
        res = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": "llama3", "prompt": prompt, "stream": False},
            timeout=3
        )
        if res.status_code == 200:
            return res.json().get("response", "").strip()
    except Exception:
        pass
        
    # Standard Rule-Based Fallback Explanation
    level = cascade_result.get("level", "LOW")
    drivers_str = ", ".join(cascade_result.get("drivers", ["ambient temperature"]))
    impact_str = ", ".join(cascade_result.get("potential_downstream_impact", ["cooling constraint"]))
    
    return (
        f"CascadeGuard risk level is {level} due to {drivers_str}. "
        f"The predicted consequence indicates {impact_str}. "
        f"Facility engineers must review and approve the recommended actions prior to execution."
    )

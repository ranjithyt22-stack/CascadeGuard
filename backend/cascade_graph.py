"""
CascadeGuard AI — Multi-Asset Engineering Cascade & Dependency Graph
Phase 11: Climate Stress What-If Simulation & Multi-Asset Cascade

Defines the engineering scenario dependency graph:
    Climate Stress ➔ Water Pump (Cooling Flow) / Chiller (Thermal Exchange) ➔ Transformer (Substation Thermal Load)

IMPORTANT:
- This dependency graph represents a configurable "Engineering Scenario Model", NOT proven physical causation.
- Water Pump risk is strictly tagged as "DECISION_SUPPORT_ONLY".
"""

import numpy as np

# Configurable Demo System Weights
DEFAULT_ASSET_WEIGHTS = {
    "transformer": 0.50,
    "chiller": 0.30,
    "water_pump": 0.20
}

DEFAULT_CLIMATE_WEIGHT = 0.20
DEFAULT_SYSTEM_ASSET_WEIGHT = 0.80

SYSTEM_THRESHOLDS = {
    "NORMAL": 25.0,
    "WATCH": 50.0,
    "WARNING": 75.0,
    "CRITICAL": 100.0
}


def get_system_risk_level(score):
    if score < SYSTEM_THRESHOLDS["NORMAL"]:
        return "NORMAL"
    elif score < SYSTEM_THRESHOLDS["WATCH"]:
        return "WATCH"
    elif score < SYSTEM_THRESHOLDS["WARNING"]:
        return "WARNING"
    return "CRITICAL"


def build_transformer_asset_schema(cascade_score, health_risk, op_risk, level):
    return {
        "asset_type": "transformer",
        "name": "Power Transformer Substation Asset",
        "risk": round(float(cascade_score), 2),
        "health_risk": round(float(health_risk), 2),
        "operational_risk": round(float(op_risk), 2),
        "status": level,
        "confidence": "HIGH",
        "source": "ML_PRODUCTION",
        "warning": None
    }


def build_chiller_asset_schema(chiller_risk, pred_class, prob_normal, prob_dict, level):
    fault_descriptions = {
        1: "Baseline Normal Operation",
        2: "Refrigerant Overcharge (High Discharge Pressure)",
        3: "Refrigerant Leakage (Low Suction Pressure)",
        4: "Condenser Water Flow Reduction / Thermal Stress",
        5: "Evaporator Water Flow Reduction / Icing Exposure",
        6: "Non-Condensable Gas Contamination in Loop",
        7: "Compressor Valve Degradation / Mechanical Drag",
        8: "Oil Sump Contamination / Pressure Drop"
    }

    desc = fault_descriptions.get(pred_class, f"Fault Mode Class {pred_class}")

    return {
        "asset_type": "chiller",
        "name": "HVAC Chiller Refrigeration Unit",
        "risk": round(float(chiller_risk), 2),
        "predicted_fault_class": int(pred_class),
        "fault_description": desc,
        "probability_normal": round(float(prob_normal), 4),
        "class_probabilities": prob_dict,
        "status": level,
        "confidence": "HIGH",
        "source": "ML_PRODUCTION",
        "warning": None
    }


def build_water_pump_asset_schema(pump_risk, pred_state, level):
    return {
        "asset_type": "water_pump",
        "name": "Industrial Cooling Water Pump",
        "risk": round(float(pump_risk), 2),
        "predicted_state": pred_state,
        "status": "DECISION_SUPPORT_ONLY",
        "confidence": "LOW",
        "source": "ML_DECISION_SUPPORT",
        "warning": "Water-pump risk signal is decision-support only due to non-stationary temporal validation limitations."
    }


def evaluate_cascade_graph(transformer_schema, chiller_schema, pump_schema, climate_data, custom_weights=None):
    weights = custom_weights if custom_weights else DEFAULT_ASSET_WEIGHTS

    w_tx = weights.get("transformer", 0.50)
    w_ch = weights.get("chiller", 0.30)
    w_wp = weights.get("water_pump", 0.20)

    # 1. System Asset Risk
    system_asset_risk = (
        w_tx * transformer_schema["risk"] +
        w_ch * chiller_schema["risk"] +
        w_wp * pump_schema["risk"]
    )
    system_asset_risk_round = round(float(system_asset_risk), 2)

    # 2. Climate Stress Integration
    climate_stress = float(climate_data.get("climate_stress", 0.0))
    system_cascade_risk = (
        DEFAULT_SYSTEM_ASSET_WEIGHT * system_asset_risk_round +
        DEFAULT_CLIMATE_WEIGHT * climate_stress
    )
    system_cascade_risk_round = round(float(np.clip(system_cascade_risk, 0.0, 100.0)), 2)
    system_level = get_system_risk_level(system_cascade_risk_round)

    # 3. Identify Most Vulnerable Asset (Confidence-Weighted Ranking)
    candidate_assets = [
        {
            "asset": "TRANSFORMER",
            "name": transformer_schema["name"],
            "raw_risk": transformer_schema["risk"],
            "confidence": transformer_schema["confidence"],
            "weighted_vulnerability": transformer_schema["risk"] * 1.0,
            "status": transformer_schema["status"]
        },
        {
            "asset": "CHILLER",
            "name": chiller_schema["name"],
            "raw_risk": chiller_schema["risk"],
            "confidence": chiller_schema["confidence"],
            "weighted_vulnerability": chiller_schema["risk"] * 1.0,
            "status": chiller_schema["status"]
        },
        {
            "asset": "WATER_PUMP",
            "name": pump_schema["name"],
            "raw_risk": pump_schema["risk"],
            "confidence": pump_schema["confidence"],
            "weighted_vulnerability": pump_schema["risk"] * 0.50,
            "status": pump_schema["status"]
        }
    ]

    candidate_assets.sort(key=lambda x: x["weighted_vulnerability"], reverse=True)
    most_vulnerable = candidate_assets[0]

    # 4. Downstream Engineering Scenario Exposure Analysis
    downstream_impacts = []

    if pump_schema["risk"] >= 40.0:
        downstream_impacts.append({
            "stage": "PUMP ➔ CHILLER",
            "severity": "MODERATE" if pump_schema["risk"] < 70.0 else "HIGH",
            "impact": "Cooling water flow reduction could increase condenser inlet water temperature (TCI) on downstream chiller units under this engineering scenario."
        })

    if chiller_schema["risk"] >= 40.0 or chiller_schema.get("predicted_fault_class") in [4, 5, 7]:
        downstream_impacts.append({
            "stage": "CHILLER ➔ TRANSFORMER",
            "severity": "MODERATE" if chiller_schema["risk"] < 70.0 else "HIGH",
            "impact": "Elevated chiller refrigeration fault risk or thermal exchange degradation could increase oil and winding thermal stress (OTI/WTI) on nearby substation transformers."
        })

    if climate_stress >= 35.0:
        downstream_impacts.append({
            "stage": "CLIMATE ➔ SYSTEM",
            "severity": "ELEVATED",
            "impact": "Ambient heatwave and solar radiation could compound heat dissipation constraints across all three infrastructure assets simultaneously."
        })

    if not downstream_impacts:
        downstream_impacts.append({
            "stage": "SYSTEM STABLE",
            "severity": "LOW",
            "impact": "Infrastructure assets are operating under stable conditions with minimal scenario cascade propagation risk."
        })

    # Human-readable engineering explanation
    if most_vulnerable["asset"] == "CHILLER":
        narrative = f"HVAC Chiller has the highest current asset risk ({chiller_schema['risk']} / 100, {chiller_schema.get('fault_description', 'Fault Mode')}). Under the configured engineering scenario, reduced thermal exchange performance could expose downstream transformer operations to additional thermal stress."
    elif most_vulnerable["asset"] == "TRANSFORMER":
        narrative = f"Power Transformer has the highest current asset risk ({transformer_schema['risk']} / 100). Elevated operational load and thermal conditions make the substation transformer the primary vulnerability point."
    else:
        narrative = f"Water Pump exhibits elevated decision-support risk ({pump_schema['risk']} / 100). Reduced cooling water circulation could increase thermal stress on the downstream chiller under the configured cascade scenario."

    return {
        "system": {
            "system_asset_risk": system_asset_risk_round,
            "climate_stress": climate_stress,
            "system_cascade_risk": system_cascade_risk_round,
            "level": system_level,
            "demo_weights": {
                "transformer_weight": w_tx,
                "chiller_weight": w_ch,
                "water_pump_weight": w_wp,
                "climate_weight": DEFAULT_CLIMATE_WEIGHT
            }
        },
        "cascade": {
            "most_vulnerable_asset": {
                "asset": most_vulnerable["asset"],
                "name": most_vulnerable["name"],
                "risk": most_vulnerable["raw_risk"],
                "confidence": most_vulnerable["confidence"],
                "status": most_vulnerable["status"]
            },
            "dependency_scenario": "Water Pump (Cooling Flow) ➔ Chiller (Thermal Exchange) ➔ Transformer (Substation Thermal Load)",
            "potential_downstream_impacts": downstream_impacts,
            "narrative": narrative
        },
        "recommendation": narrative,
        "limitations": [
            "Water pump risk signal is designated DECISION_SUPPORT_ONLY due to out-of-time validation limitations.",
            "Cascade dependencies represent configurable engineering scenarios, not observed physical causation.",
            "Datasets do not establish a physical facility topology."
        ]
    }


def generate_scenario_recommendation(scenario_name, delta, most_vulnerable):
    name = str(scenario_name).upper().strip()
    if name == "HEATWAVE":
        return f"Increase attention to HVAC chiller condenser conditions and monitor substation transformer thermal loading under simulated heatwave stress (System Risk +{delta:.1f})."
    elif name == "EXTREME_HEAT":
        return f"Extreme ambient heat surge could severely degrade heat dissipation across all units. Evaluate supplementary cooling deployment and monitor transformer winding thermal stress (System Risk +{delta:.1f})."
    elif name == "HIGH_HUMIDITY":
        return f"High humidity scenario may reduce evaporative cooling effectiveness. Inspect chiller cooling tower airflow and motor winding insulation."
    elif name == "HEAVY_RAIN":
        return f"Heavy rain scenario may risk water ingress and electrical surface creepage. Inspect transformer bushing enclosures and outdoor pump housings."
    elif name == "COOLING_FAILURE":
        return f"HVAC Chiller restriction simulation. Inspect cooling-system availability and evaluate potential thermal stress propagation to nearby substation transformers."
    elif name == "PUMP_DEGRADATION":
        return f"Cooling water pump degradation simulation. Evaluate cooling-flow availability before relying on downstream equipment risk estimates."
    elif name == "COMBINED_CASCADE":
        return f"Prioritize comprehensive engineering assessment of interconnected cooling and electrical infrastructure under compound extreme stress."
    return "Maintain baseline monitoring across power transformer, HVAC chiller, and cooling water pump assets."


def evaluate_cascade_scenario(transformer_schema, chiller_schema, pump_schema, climate_scenario_res):
    # 1. Baseline Evaluation
    b_climate = climate_scenario_res["baseline"]
    baseline_eval = evaluate_cascade_graph(transformer_schema, chiller_schema, pump_schema, b_climate)
    b_score = baseline_eval["system"]["system_cascade_risk"]

    # 2. Scenario Evaluation
    s_climate = climate_scenario_res["scenario"]
    scen_name = climate_scenario_res["scenario_name"]

    # Adjust asset scenario risks if scenario induces direct asset stress
    s_tx_risk = transformer_schema["risk"]
    s_ch_risk = chiller_schema["risk"]
    s_wp_risk = pump_schema["risk"]

    if scen_name in ["HEATWAVE", "EXTREME_HEAT"]:
        delta_stress = climate_scenario_res["stress_change"]
        s_tx_risk = float(np.clip(s_tx_risk + delta_stress * 0.40, 0.0, 100.0))
        s_ch_risk = float(np.clip(s_ch_risk + delta_stress * 0.50, 0.0, 100.0))
    elif scen_name == "COOLING_FAILURE":
        s_ch_risk = float(np.clip(s_ch_risk + 35.0, 0.0, 100.0))
        s_tx_risk = float(np.clip(s_tx_risk + 15.0, 0.0, 100.0))
    elif scen_name == "PUMP_DEGRADATION":
        s_wp_risk = float(np.clip(s_wp_risk + 40.0, 0.0, 100.0))
        s_ch_risk = float(np.clip(s_ch_risk + 20.0, 0.0, 100.0))
    elif scen_name == "COMBINED_CASCADE":
        s_tx_risk = float(np.clip(s_tx_risk + 30.0, 0.0, 100.0))
        s_ch_risk = float(np.clip(s_ch_risk + 45.0, 0.0, 100.0))
        s_wp_risk = float(np.clip(s_wp_risk + 35.0, 0.0, 100.0))

    s_tx_schema = build_transformer_asset_schema(s_tx_risk, transformer_schema.get("health_risk", 0), transformer_schema.get("operational_risk", 0), get_system_risk_level(s_tx_risk))
    s_ch_schema = build_chiller_asset_schema(s_ch_risk, chiller_schema.get("predicted_fault_class", 1), chiller_schema.get("probability_normal", 0.95), chiller_schema.get("class_probabilities", {}), get_system_risk_level(s_ch_risk))
    s_wp_schema = build_water_pump_asset_schema(s_wp_risk, pump_schema.get("predicted_state", "NORMAL"), get_system_risk_level(s_wp_risk))

    scenario_eval = evaluate_cascade_graph(s_tx_schema, s_ch_schema, s_wp_schema, s_climate)
    s_score = scenario_eval["system"]["system_cascade_risk"]
    delta_score = round(s_score - b_score, 2)

    # 3. Define Cascade Step Path
    cascade_path = [
        {"node": "CLIMATE STRESS", "val": f"{s_climate['climate_stress']} / 100", "label": "Simulated Ambient Heat & Weather"},
        {"node": "WATER PUMP", "val": f"{s_wp_risk:.1f} / 100", "label": "Cooling Water Circulation (Decision Support)"},
        {"node": "HVAC CHILLER", "val": f"{s_ch_risk:.1f} / 100", "label": "Thermal Exchange & Refrigerant Loop"},
        {"node": "POWER TRANSFORMER", "val": f"{s_tx_risk:.1f} / 100", "label": "Substation Operational Load & Thermal Stress"},
        {"node": "SYSTEM CASCADE RISK", "val": f"{s_score:.1f} / 100", "label": "Weighted Multi-Asset Scenario Risk"}
    ]

    rec = generate_scenario_recommendation(scen_name, delta_score, scenario_eval["cascade"]["most_vulnerable_asset"])

    return {
        "baseline_risk": b_score,
        "scenario_risk": s_score,
        "change": delta_score,
        "level": get_system_risk_level(s_score),
        "assets": {
            "transformer": s_tx_schema,
            "chiller": s_ch_schema,
            "water_pump": s_wp_schema
        },
        "cascade_path": cascade_path,
        "path_notice": "ENGINEERING SCENARIO — NOT OBSERVED FAILURE",
        "recommendation": rec
    }

"""
CascadeGuard AI — Decision-Support Recommendation Engine
Phase 13: Incident Intelligence + Automated Alerting + Executive Report

Maps asset risk scores, climate stress conditions, and OT simulation scenarios to actionable,
non-causal engineering decision-support recommendations.
"""

def generate_recommendations(system_risk, assets_dict, climate_dict, active_scenario="NORMAL"):
    """
    Generates structured decision-support recommendations based on asset & climate evaluation.
    All outputs are explicitly designated as advisory decision-support recommendations.
    """
    recs = []
    
    tx = assets_dict.get("transformer", {})
    ch = assets_dict.get("chiller", {})
    wp = assets_dict.get("water_pump", {})
    
    tx_risk = tx.get("cascade_risk_score", tx.get("risk_score", 0.0))
    ch_risk = ch.get("chiller_risk_score", ch.get("risk_score", 0.0))
    wp_risk = wp.get("pump_risk_score", wp.get("risk_score", 0.0))
    climate_stress = climate_dict.get("overall_climate_stress", climate_dict.get("climate_stress", 0.0))

    # 1. Power Transformer Recommendations
    if tx_risk >= 60.0 or active_scenario in ["HIGH_LOAD", "COMBINED_CASCADE"]:
        recs.append({
            "asset": "TRANSFORMER",
            "category": "THERMAL_MANAGEMENT",
            "priority": "HIGH" if tx_risk >= 75.0 else "MEDIUM",
            "action": "Inspect transformer thermal loading & active cooling fan status",
            "rationale": f"Transformer cascade risk score is elevated ({tx_risk:.1f}/100). May indicate top-oil heat dissipation stress under load."
        })
        recs.append({
            "asset": "TRANSFORMER",
            "category": "MONITORING",
            "priority": "MEDIUM",
            "action": "Verify oil and winding temperature trends (OTI & WTI)",
            "rationale": "High thermal accumulation could accelerate winding insulation aging if sustained."
        })

    # 2. HVAC Chiller Recommendations
    if ch_risk >= 50.0 or active_scenario in ["CHILLER_OVERLOAD", "PUMP_DEGRADATION", "COMBINED_CASCADE"]:
        recs.append({
            "asset": "CHILLER",
            "category": "COOLING_EFFICIENCY",
            "priority": "HIGH" if ch_risk >= 75.0 else "MEDIUM",
            "action": "Inspect condenser heat exchanger coils & verify condenser water flow",
            "rationale": f"HVAC Chiller risk score is elevated ({ch_risk:.1f}/100). High condenser entering temperature (TCI) degrades compressor COP."
        })
        recs.append({
            "asset": "CHILLER",
            "category": "ELECTRICAL_LOAD",
            "priority": "MEDIUM",
            "action": "Check compressor motor electrical demand and power factor",
            "rationale": "Elevated compressor power surge contributes to auxiliary plant power demand."
        })

    # 3. Water Pump Recommendations (Decision Support Only)
    if wp_risk >= 40.0 or active_scenario in ["PUMP_DEGRADATION", "COMBINED_CASCADE"]:
        recs.append({
            "asset": "WATER_PUMP",
            "category": "HYDRAULIC_FLOW",
            "priority": "HIGH" if wp_risk >= 70.0 else "MEDIUM",
            "action": "Verify cooling-water flow rate and system delivery pressure",
            "rationale": f"Water Pump decision-support risk is elevated ({wp_risk:.1f}/100). Reduced hydraulic flow reduces condenser heat rejection capacity."
        })
        recs.append({
            "asset": "WATER_PUMP",
            "category": "MECHANICAL_HEALTH",
            "priority": "MEDIUM",
            "action": "Inspect pump motor temperature and vibration telemetry",
            "rationale": "Flow restriction or bearing wear may increase motor thermal stress."
        })

    # 4. Climate Stress Recommendations
    if climate_stress >= 35.0 or climate_dict.get("heatwave", {}).get("detected", False):
        recs.append({
            "asset": "CLIMATE",
            "category": "GRID_OPERATIONS",
            "priority": "MEDIUM",
            "action": "Increase monitoring frequency and evaluate peak load reduction options",
            "rationale": f"Ambient climate stress is high ({climate_stress:.1f}/100) under heatwave conditions."
        })

    # Default fallback baseline recommendation
    if len(recs) == 0:
        recs.append({
            "asset": "SYSTEM",
            "category": "ROUTINE",
            "priority": "LOW",
            "action": "Maintain routine multi-asset monitoring and telemetry stream validation",
            "rationale": "All asset risk scores and climate stress metrics are operating within normal baseline limits."
        })

    return {
        "disclaimer": "Decision-support recommendations for engineering review — NOT autonomous control actions.",
        "count": len(recs),
        "actions": recs
    }

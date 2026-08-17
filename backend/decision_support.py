def generate_decision_support(cascade_score, level, early_warning, trend, top_factors, climate, scenario_name="NORMAL"):
    actions = []
    
    # 1. Base Level Action
    if level == "LOW":
        actions.append("Maintain baseline automated substation telemetry monitoring.")
    elif level == "MODERATE":
        actions.append("Increase telemetry sampling frequency and review recent thermal loading trends.")
    elif level == "HIGH":
        actions.append("Prioritize physical transformer inspection; evaluate load reduction or forced cooling activation.")
    else:  # CRITICAL
        actions.append("Initiate immediate emergency engineering assessment and evaluate protective load redistribution.")

    # 2. Factor-Specific Engineering Guidance
    top_feature_names = [f["feature"] for f in top_factors] if top_factors else []

    if any(feat in top_feature_names for feat in ["OTI", "WTI", "OTI_roll30m_mean", "OTI_roll60m_mean"]):
        actions.append("Review oil/winding cooling radiator fans and oil circulation pumps.")

    if any(feat in top_feature_names for feat in ["MPD_roll60m_mean", "KW_roll30m_mean", "KW", "KVA", "MPD"]):
        actions.append("High peak active power demand detected; evaluate load shedding or sub-station load balancing.")

    if any(feat in top_feature_names for feat in ["THDVL1_roll60m_mean", "THDVL1_roll30m_mean", "THDVL1", "THDIL1"]):
        actions.append("Elevated harmonic distortion detected; inspect active harmonic filters and capacitor banks.")

    if any(feat in top_feature_names for feat in ["ATI", "ATI_roll30m_mean"]) or climate.get("temperature", 0) > 38:
        actions.append("High ambient temperature stress; monitor solar radiation shading and cooling efficiency.")

    if climate.get("rain", 0) > 20.0 or climate.get("humidity", 0) > 90.0:
        actions.append("Heavy moisture/rainfall detected; verify substation drainage and moisture seal integrity.")

    if scenario_name == "DGA_DEGRADED" or any(feat in top_feature_names for feat in ["Hydrogen", "Methane", "Acethylene"]):
        actions.append("Dissolved gas anomaly detected; schedule oil gas-chromatography analysis for internal arcing/overheating.")

    # 3. Trend Guidance
    if trend == "RISING":
        actions.append("Risk trend is RISING; trigger pre-emptive alert for field maintenance operations.")

    summary_action = actions[0]
    detailed_guidance = " | ".join(actions)

    return {
        "summary": summary_action,
        "detailed_guidance": detailed_guidance,
        "recommended_actions": actions,
        "disclaimer": "AI-assisted decision support for utility operators, not autonomous grid control commands."
    }

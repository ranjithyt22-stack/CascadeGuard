"""
backend/services/recommendation_engine_phase17.py
===================================================
Phase 17 — Predictive Climate Risk & Facility Failure Forecasting

Recommendation Engine generating actionable preventive recommendations
based on facility climate risk, equipment risk levels, and forecast trends.
"""

from typing import Dict, Any, List


def generate_facility_recommendations(
    facility_name: str,
    facility_risk: float,
    equipment_risks: Dict[str, Any],
    weather_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Generates prioritized, actionable preventive recommendations for a facility."""
    recommendations = []
    
    tx_info = equipment_risks.get("transformer", {})
    ch_info = equipment_risks.get("chiller", {})
    wp_info = equipment_risks.get("water_pump", {})

    peak_temp = float(weather_data.get("peak_forecast_temp", weather_data.get("temperature", 28.5)))
    rain_prob = float(weather_data.get("rain_probability", weather_data.get("precipitation_probability", 0.0)))
    curr_rain = float(weather_data.get("rain", 0.0))

    # Priority 1: High/Critical Transformer Risk
    if tx_info.get("risk_category") in ["CRITICAL", "HIGH"]:
        recommendations.append({
            "priority": 1,
            "equipment_id": tx_info.get("equipment_id", "Transformer"),
            "equipment_type": "Transformer",
            "urgency": tx_info.get("risk_category"),
            "title": "Transformer Thermal Overload Mitigation",
            "action": f"Inspect transformer cooling oil circulation fans, verify OTI readings, and prepare load-shedding for non-essential plant operations before ambient temperature reaches forecast peak of {peak_temp}°C.",
            "expected_window": "6–18 Hours"
        })

    # Priority 2: High/Critical Chiller Risk
    if ch_info.get("risk_category") in ["CRITICAL", "HIGH"]:
        recommendations.append({
            "priority": len(recommendations) + 1,
            "equipment_id": ch_info.get("equipment_id", "Chiller"),
            "equipment_type": "HVAC Chiller",
            "urgency": ch_info.get("risk_category"),
            "title": "HVAC Chiller Condenser Pre-Cooling",
            "action": f"Pre-cool plant facility areas during lower ambient temperature window and inspect condenser heat-rejection coils to avoid thermal tripping.",
            "expected_window": "12–24 Hours"
        })

    # Priority 3: High/Critical Water Pump Risk
    if wp_info.get("risk_category") in ["CRITICAL", "HIGH"] or rain_prob >= 70.0 or curr_rain >= 15.0:
        recommendations.append({
            "priority": len(recommendations) + 1,
            "equipment_id": wp_info.get("equipment_id", "Water Pump"),
            "equipment_type": "Water Pump",
            "urgency": wp_info.get("risk_category", "HIGH"),
            "title": "Flood & Heavy Rainfall Drainage Clearance",
            "action": f"Verify drainage sump pump power connections, clear debris from runoff channels, and confirm emergency drainage pump availability (heavy rain probability: {rain_prob}%).",
            "expected_window": "3–6 Hours"
        })

    # Default baseline recommendation if all are low/moderate
    if not recommendations:
        recommendations.append({
            "priority": 1,
            "equipment_id": "FACILITY_WIDE",
            "equipment_type": "Facility Infrastructure",
            "urgency": "NORMAL",
            "title": "Routine Baseline Climate Risk Monitoring",
            "action": f"Facility {facility_name} operating within normal risk parameters. Maintain standard 24/7 telemetry monitoring.",
            "expected_window": "Continuous"
        })

    return recommendations

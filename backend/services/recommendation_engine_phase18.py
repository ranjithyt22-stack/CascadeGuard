"""
backend/services/recommendation_engine_phase18.py
===================================================
Phase 18 — AI-Powered Climate Resilience Decision & Response Engine

Recommendation Engine Phase 18 generating explainable, climate-driver specific
operational action decisions with confidence scoring and benefit analysis.
"""

import numpy as np
from typing import Dict, Any, List


class RecommendationEnginePhase18:
    """Generates structured, explainable action decisions tailored to climate drivers."""

    def identify_climate_driver(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """Identifies primary climate risk driver (HEAT, HEAVY_RAIN, HIGH_HUMIDITY, EXTREME_WEATHER)."""
        temp = float(weather_data.get("temperature", 28.5))
        peak_temp = float(weather_data.get("peak_forecast_temp", temp))
        hum = float(weather_data.get("humidity", 60.0))
        rain = float(weather_data.get("rain", 0.0))
        rain_prob = float(weather_data.get("rain_probability", weather_data.get("precipitation_probability", 0.0)))
        wind = float(weather_data.get("wind", 12.0))

        drivers = []
        if peak_temp >= 35.0 or temp >= 35.0:
            drivers.append(("HEAT", max(temp, peak_temp) - 30.0))
        if rain >= 10.0 or rain_prob >= 65.0:
            drivers.append(("HEAVY_RAIN", rain * 2.0 + rain_prob * 0.5))
        if hum >= 75.0:
            drivers.append(("HIGH_HUMIDITY", hum - 50.0))
        if wind >= 35.0:
            drivers.append(("HIGH_WIND", wind - 20.0))

        if not drivers:
            return {"primary_driver": "NORMAL", "description": "Ambient conditions within standard operating thresholds."}

        drivers.sort(key=lambda x: x[1], reverse=True)
        primary = drivers[0][0]

        desc_map = {
            "HEAT": f"Extreme ambient temperature (forecast peak: {peak_temp}°C) increasing thermal dissipation load.",
            "HEAVY_RAIN": f"High precipitation probability ({rain_prob}%) and rainfall ({rain} mm) creating surface flood risk.",
            "HIGH_HUMIDITY": f"Elevated relative humidity ({hum}%) impeding condenser heat rejection.",
            "HIGH_WIND": f"High wind speed ({wind} km/h) creating structural environmental strain."
        }

        return {
            "primary_driver": primary,
            "description": desc_map.get(primary, "Elevated environmental stress detected.")
        }

    def generate_action_decision(
        self,
        site_name: str,
        equipment_id: str,
        equipment_type: str,
        risk_score: float,
        weather_data: Dict[str, Any],
        impact_info: Dict[str, Any],
        urgency_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generates explainable action decision with WHY, WHAT, WHEN, PRIORITY, EXPECTED BENEFIT,
        responsible operational area, and decision confidence score.
        """
        eq_type = str(equipment_type).upper().replace(" ", "_")
        driver_info = self.identify_climate_driver(weather_data)
        driver = driver_info["primary_driver"]

        timeframe = urgency_info.get("recommended_timeframe", "Within 6 Hours")
        urgency_lvl = urgency_info.get("urgency_level", "MODERATE")
        impact_lvl = impact_info.get("impact_level", "MODERATE")

        # Responsible Operational Team
        if "TRANSFORMER" in eq_type:
            team = "Electrical Operations & Substation Maintenance"
        elif "CHILLER" in eq_type:
            team = "HVAC & Thermal Plant Engineering"
        elif "PUMP" in eq_type:
            team = "Facilities & Civil Drainage Operations"
        else:
            team = "Facility Operations Management"

        # Structured Action Matrix based on Equipment + Driver + Risk Level
        if "TRANSFORMER" in eq_type:
            if risk_score >= 75.0 or urgency_lvl == "CRITICAL":
                action = f"Inspect transformer {equipment_id} oil cooling system, activate auxiliary cooling fans, and shed non-essential load."
                why = f"Forecast peak temperature ({weather_data.get('peak_forecast_temp', 35)}°C) combined with high transformer thermal stress risks exceeding oil insulation limits."
                benefit = "Prevents transformer winding thermal trip and avoids major substation outage."
                priority = "CRITICAL"
            elif risk_score >= 50.0:
                action = f"Monitor transformer {equipment_id} oil/winding temperatures closely and rebalance phase loading."
                why = f"Sustained ambient heat ({driver_info['description']}) is increasing transformer operating baseline."
                benefit = "Reduces rate of oil degradation and maintains safe operating margin."
                priority = "HIGH"
            else:
                action = f"Continue routine monitoring for transformer {equipment_id}."
                why = "Transformer operating parameters within safe baseline limits."
                benefit = "Saves operational overhead."
                priority = "LOW"

        elif "CHILLER" in eq_type:
            if risk_score >= 70.0 or driver == "HIGH_HUMIDITY" and risk_score >= 50.0:
                action = f"Pre-cool facility during lower-demand window and inspect chiller {equipment_id} condenser heat rejection."
                why = f"High ambient humidity ({weather_data.get('humidity', 60)}%) impedes condenser heat dissipation while cooling demand surges."
                benefit = "Avoids chiller high-pressure safety trip and keeps building HVAC online."
                priority = "HIGH" if risk_score < 75 else "CRITICAL"
            elif risk_score >= 45.0:
                action = f"Verify chilled water circulation pump flow and clean condenser air intake filters for chiller {equipment_id}."
                why = "Elevated ambient heat increases HVAC compression ratio requirement."
                benefit = "Optimizes chiller coefficient of performance (COP)."
                priority = "MODERATE"
            else:
                action = f"Maintain normal chiller {equipment_id} cooling setpoint."
                why = "HVAC cooling demand is within standard capacity."
                benefit = "Standard energy consumption."
                priority = "LOW"

        elif "PUMP" in eq_type:
            if driver == "HEAVY_RAIN" or risk_score >= 60.0:
                action = f"Inspect water pump {equipment_id} sump pit, clear drainage strainers, and confirm emergency standby power."
                why = f"Heavy rainfall probability ({weather_data.get('rain_probability', 0)}%) risks sump waterlogging and pump cavitation."
                benefit = "Prevents basement/substation water ingress and pump motor submergence."
                priority = "HIGH" if risk_score < 75 else "CRITICAL"
            else:
                action = f"Perform routine mechanical check on water pump {equipment_id} seal condition."
                why = "Normal environmental drainage conditions."
                benefit = "Ensures standby pump readiness."
                priority = "LOW"
        else:
            action = f"Inspect facility infrastructure asset {equipment_id}."
            why = "General climate stress monitoring."
            benefit = "Maintains asset longevity."
            priority = "MODERATE"

        # Calculate Decision Confidence (0-100%)
        # Weather LIVE: +50, Telemetry present: +35, Forecast data completeness: +15
        is_live = bool(weather_data.get("realtime", False) or weather_data.get("source_status") == "LIVE")
        conf_score = (50.0 if is_live else 30.0) + 35.0 + 15.0
        conf_score = round(float(np.clip(conf_score, 40.0, 95.0)), 1)

        conf_level = "HIGH" if conf_score >= 80.0 else ("MODERATE" if conf_score >= 50.0 else "LOW")

        return {
            "equipment_id": equipment_id,
            "equipment_type": equipment_type,
            "primary_climate_driver": driver,
            "action": action,
            "why": why,
            "when_timeframe": timeframe,
            "priority": priority,
            "expected_benefit": benefit,
            "responsible_team": team,
            "decision_confidence_pct": conf_score,
            "confidence_level": conf_level,
            "decision_mode": "AI-Assisted Decision Engine",
            "follow_up_condition": "Re-evaluate risk score after 2 hours of telemetry ingestion or upon updated Open-Meteo forecast."
        }


recommendation_engine_p18 = RecommendationEnginePhase18()

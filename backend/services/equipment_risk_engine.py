"""
backend/services/equipment_risk_engine.py
=========================================
Phase 17 — Predictive Climate Risk & Facility Failure Forecasting

Equipment Risk Engine for Transformer, Chiller, and Water Pump risk prediction.
Supports both Rule-based Risk Estimates and ML Model Predictions.
"""

import numpy as np
from typing import Dict, Any


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


class BaseEquipmentRiskPredictor:
    """Base class for equipment-specific risk predictors."""
    def predict_risk(self, equipment_id: str, weather_data: Dict[str, Any], telemetry_data: Dict[str, Any] = None) -> Dict[str, Any]:
        raise NotImplementedError


class TransformerRiskPredictor(BaseEquipmentRiskPredictor):
    """Predictor for Power Transformer climate & operational failure risk."""

    def predict_risk(self, equipment_id: str, weather_data: Dict[str, Any], telemetry_data: Dict[str, Any] = None) -> Dict[str, Any]:
        telemetry = telemetry_data or {}
        curr_temp = float(weather_data.get("temperature", 28.5))
        peak_temp = float(weather_data.get("peak_forecast_temp", weather_data.get("forecast_peak_temp", curr_temp)))
        humidity = float(weather_data.get("humidity", 60.0))
        climate_stress = float(weather_data.get("climate_stress", 30.0))

        # Operational telemetry features if available, scale by temperature difference
        ati_base = float(telemetry.get("ATI", curr_temp))
        temp_diff = curr_temp - ati_base
        oti = float(telemetry.get("OTI", curr_temp + 15.0)) + temp_diff
        wti = float(telemetry.get("WTI", curr_temp + 20.0)) + temp_diff
        kw_load = float(telemetry.get("KW", telemetry.get("power", 120.0)))
        
        # Thermal margin calculation (max safe winding temp is 110°C)
        max_safe_temp = 110.0
        thermal_margin = max(0.0, max_safe_temp - wti)

        # Thermal stress components
        heat_stress = float(np.clip((peak_temp - 30.0) / 15.0 * 100.0, 0.0, 100.0))
        oti_stress = float(np.clip((oti - 55.0) / 40.0 * 100.0, 0.0, 100.0))
        load_stress = float(np.clip((kw_load - 100.0) / 150.0 * 100.0, 0.0, 100.0))

        # Risk score calculation
        risk_score = 0.35 * heat_stress + 0.30 * oti_stress + 0.20 * load_stress + 0.15 * climate_stress
        risk_score = float(np.clip(risk_score, 0.0, 100.0))
        round_score = round(risk_score, 2)
        category = get_risk_category(round_score)

        # Failure probability estimate (0-100%)
        failure_prob_pct = round(float(np.clip(1.0 / (1.0 + np.exp(-(risk_score - 50.0) / 12.0)) * 100.0, 1.0, 99.0)), 2)

        # Recommendation
        if category == "CRITICAL":
            recommendation = f"Inspect transformer {equipment_id} cooling system immediately, deploy auxiliary fans, and reduce non-essential load."
        elif category == "HIGH":
            recommendation = f"Monitor transformer {equipment_id} oil/winding temperatures closely and evaluate load-balancing options."
        elif category == "MODERATE":
            recommendation = f"Schedule routine cooling radiator inspection for transformer {equipment_id} during lower-demand periods."
        else:
            recommendation = f"Transformer {equipment_id} operating within normal thermal and load parameters."

        return {
            "equipment_id": equipment_id,
            "equipment_type": "transformer",
            "risk_score": round_score,
            "failure_probability_pct": failure_prob_pct,
            "risk_category": category,
            "prediction_mode": "ML Failure Prediction" if "operational_risk" in telemetry else "Predictive Risk Estimate",
            "metrics": {
                "current_temperature": curr_temp,
                "forecast_peak_temperature": peak_temp,
                "oil_temperature": oti,
                "winding_temperature": wti,
                "active_load_kw": kw_load,
                "climate_stress": climate_stress,
                "thermal_margin_c": round(thermal_margin, 1),
                "max_safe_winding_temp_c": max_safe_temp
            },
            "recommended_action": recommendation
        }


class ChillerRiskPredictor(BaseEquipmentRiskPredictor):
    """Predictor for HVAC Chiller thermal stress & cooling demand failure risk."""

    def predict_risk(self, equipment_id: str, weather_data: Dict[str, Any], telemetry_data: Dict[str, Any] = None) -> Dict[str, Any]:
        telemetry = telemetry_data or {}
        curr_temp = float(weather_data.get("temperature", 28.5))
        peak_temp = float(weather_data.get("peak_forecast_temp", weather_data.get("forecast_peak_temp", curr_temp)))
        humidity = float(weather_data.get("humidity", 60.0))
        climate_stress = float(weather_data.get("climate_stress", 30.0))

        # Extract chiller operating telemetry variables
        chiller_load = float(telemetry.get("load_pct", 65.0))
        cop = float(telemetry.get("cop", 4.0))

        # Heat rejection drag increases with high ambient humidity and high peak temp
        heat_rejection_drag = float(np.clip(((curr_temp - 28.0) * 0.6 + (humidity - 50.0) * 0.4), 0.0, 100.0))
        cooling_demand_stress = float(np.clip((peak_temp - 25.0) / 20.0 * 100.0, 0.0, 100.0))
        
        # Compressor stress increases with high load and decaying COP efficiency
        chiller_stress = float(np.clip(chiller_load * 0.6 + (5.0 - cop) * 10.0, 0.0, 100.0))

        # Combined chiller risk score
        risk_score = 0.35 * cooling_demand_stress + 0.25 * heat_rejection_drag + 0.20 * chiller_stress + 0.20 * climate_stress
        risk_score = float(np.clip(risk_score, 0.0, 100.0))
        round_score = round(risk_score, 2)
        category = get_risk_category(round_score)

        failure_prob_pct = round(float(np.clip(1.0 / (1.0 + np.exp(-(risk_score - 48.0) / 11.0)) * 100.0, 1.0, 99.0)), 2)

        if cooling_demand_stress >= 75.0:
            cooling_demand_level = "VERY HIGH"
        elif cooling_demand_stress >= 50.0:
            cooling_demand_level = "ELEVATED"
        elif cooling_demand_stress >= 25.0:
            cooling_demand_level = "MODERATE"
        else:
            cooling_demand_level = "NORMAL"

        if category in ["CRITICAL", "HIGH"]:
            recommendation = f"Pre-cool facility during lower-load period, clean condenser coils, and inspect chiller {equipment_id} compressor performance."
        elif category == "MODERATE":
            recommendation = f"Monitor chiller {equipment_id} refrigerant pressure and condenser fan operation."
        else:
            recommendation = f"Chiller {equipment_id} cooling load and condenser heat rejection operate normally."

        return {
            "equipment_id": equipment_id,
            "equipment_type": "chiller",
            "risk_score": round_score,
            "failure_probability_pct": failure_prob_pct,
            "risk_category": category,
            "cooling_demand_level": cooling_demand_level,
            "prediction_mode": "Predictive Risk Estimate",
            "metrics": {
                "cooling_demand_stress": round(cooling_demand_stress, 2),
                "heat_rejection_drag": round(heat_rejection_drag, 2),
                "ambient_humidity_pct": humidity,
                "climate_stress": climate_stress,
                "chiller_load_pct": chiller_load,
                "cop": cop,
                "chiller_stress": chiller_stress
            },
            "recommended_action": recommendation
        }


class WaterPumpRiskPredictor(BaseEquipmentRiskPredictor):
    """Predictor for Industrial Water Pump flooding, heavy rainfall, and motor stress risk."""

    def predict_risk(self, equipment_id: str, weather_data: Dict[str, Any], telemetry_data: Dict[str, Any] = None) -> Dict[str, Any]:
        telemetry = telemetry_data or {}
        curr_rain = float(weather_data.get("rain", 0.0))
        rain_prob = float(weather_data.get("rain_probability", weather_data.get("precipitation_probability", 0.0)))
        climate_stress = float(weather_data.get("climate_stress", 30.0))

        # Extract water pump operating telemetry variables
        pump_load = float(telemetry.get("load_pct", 60.0))
        vibration = float(telemetry.get("vibration", 1.5))

        # Rain & flood stress
        rain_amount_stress = float(np.clip(curr_rain / 25.0 * 100.0, 0.0, 100.0))
        flood_drainage_risk = float(np.clip(rain_amount_stress * 0.6 + rain_prob * 0.4, 0.0, 100.0))
        
        # Pump mechanical/electrical stress increases with load and vibration
        pump_stress = float(np.clip(pump_load * 0.5 + (vibration - 1.5) / 6.0 * 100.0, 0.0, 100.0))

        risk_score = 0.35 * flood_drainage_risk + 0.25 * rain_amount_stress + 0.20 * pump_stress + 0.20 * climate_stress
        risk_score = float(np.clip(risk_score, 0.0, 100.0))
        round_score = round(risk_score, 2)
        category = get_risk_category(round_score)

        failure_prob_pct = round(float(np.clip(1.0 / (1.0 + np.exp(-(risk_score - 52.0) / 13.0)) * 100.0, 1.0, 99.0)), 2)

        if category in ["CRITICAL", "HIGH"]:
            recommendation = f"Inspect facility drainage sumps, clear debris, and verify emergency standby availability for water pump {equipment_id}."
        elif category == "MODERATE":
            recommendation = f"Check water pump {equipment_id} seal condition and discharge line flow rate ahead of expected rainfall."
        else:
            recommendation = f"Water pump {equipment_id} drainage capacity and environmental stress level are normal."

        return {
            "equipment_id": equipment_id,
            "equipment_type": "water_pump",
            "risk_score": round_score,
            "failure_probability_pct": failure_prob_pct,
            "risk_category": category,
            "flood_drainage_risk": round(flood_drainage_risk, 2),
            "heavy_rain_probability_pct": rain_prob,
            "prediction_mode": "Predictive Risk Estimate (Decision Support)",
            "metrics": {
                "current_rainfall_mm": curr_rain,
                "rain_probability_pct": rain_prob,
                "flood_risk_score": round(flood_drainage_risk, 2),
                "climate_stress": climate_stress,
                "pump_load_pct": pump_load,
                "vibration_mms": vibration,
                "pump_stress": pump_stress
            },
            "recommended_action": recommendation
        }


class EquipmentRiskEngine:
    """Unified engine delegating to equipment-specific risk predictors."""

    def __init__(self):
        self.transformer_predictor = TransformerRiskPredictor()
        self.chiller_predictor = ChillerRiskPredictor()
        self.water_pump_predictor = WaterPumpRiskPredictor()

    def predict_all_equipment_risk(
        self, site_data: Dict[str, Any], weather_data: Dict[str, Any], telemetry_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        asset_ids = site_data.get("asset_ids", {})
        tx_id = asset_ids.get("transformer", "TX-001")
        ch_id = asset_ids.get("chiller", "CH-001")
        wp_id = asset_ids.get("water_pump", "WP-001")

        tx_pred = self.transformer_predictor.predict_risk(tx_id, weather_data, telemetry_data)
        ch_pred = self.chiller_predictor.predict_risk(ch_id, weather_data, telemetry_data)
        wp_pred = self.water_pump_predictor.predict_risk(wp_id, weather_data, telemetry_data)

        return {
            "transformer": tx_pred,
            "chiller": ch_pred,
            "water_pump": wp_pred
        }


equipment_risk_engine = EquipmentRiskEngine()

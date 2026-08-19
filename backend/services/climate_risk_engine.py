"""
backend/services/climate_risk_engine.py
========================================
Phase 17 — Predictive Climate Risk & Facility Failure Forecasting

Climate Feature Extraction & Facility Climate Risk Engine.
Provides centralized, configurable climate thresholds and normalized scoring
for temperature, humidity, rainfall, apparent temperature, and extreme weather.
"""

import numpy as np
from typing import Dict, Any

# Centralized Configurable Climate Thresholds
CLIMATE_THRESHOLDS = {
    "temperature": {
        "low_max": 30.0,        # 0-30°C -> Low stress
        "moderate_max": 35.0,   # 30-35°C -> Moderate stress
        "high_max": 40.0,       # 35-40°C -> High stress
        "critical_min": 40.0    # >40°C -> Critical stress
    },
    "humidity": {
        "low_max": 50.0,
        "moderate_max": 70.0,
        "high_max": 85.0
    },
    "rainfall": {
        "low_max": 5.0,       # mm/h
        "moderate_max": 15.0,
        "high_max": 30.0
    },
    "heat_index": {
        "warning_temp": 38.0,
        "danger_temp": 42.0
    },
    "weights": {
        "temperature": 0.35,
        "humidity": 0.15,
        "rainfall": 0.20,
        "extreme_weather": 0.20,
        "forecast_trend": 0.10
    }
}


def get_temperature_stress(temp_c: float) -> Dict[str, Any]:
    """Calculates temperature stress score (0-100) and risk category based on thresholds."""
    temp = float(temp_c)
    t_cfg = CLIMATE_THRESHOLDS["temperature"]

    if temp <= t_cfg["low_max"]:
        score = max(0.0, (temp / t_cfg["low_max"]) * 25.0)
        level = "LOW"
    elif temp <= t_cfg["moderate_max"]:
        score = 25.0 + ((temp - t_cfg["low_max"]) / (t_cfg["moderate_max"] - t_cfg["low_max"])) * 25.0
        level = "MODERATE"
    elif temp <= t_cfg["high_max"]:
        score = 50.0 + ((temp - t_cfg["moderate_max"]) / (t_cfg["high_max"] - t_cfg["moderate_max"])) * 25.0
        level = "HIGH"
    else:
        score = 75.0 + min(25.0, ((temp - t_cfg["high_max"]) / 10.0) * 25.0)
        level = "CRITICAL"

    return {
        "score": round(float(np.clip(score, 0.0, 100.0)), 2),
        "level": level,
        "value": temp
    }


def get_humidity_stress(humidity_pct: float) -> Dict[str, Any]:
    """Calculates relative humidity stress score (0-100)."""
    hum = float(humidity_pct)
    h_cfg = CLIMATE_THRESHOLDS["humidity"]

    if hum <= h_cfg["low_max"]:
        score = (hum / h_cfg["low_max"]) * 25.0
        level = "LOW"
    elif hum <= h_cfg["moderate_max"]:
        score = 25.0 + ((hum - h_cfg["low_max"]) / (h_cfg["moderate_max"] - h_cfg["low_max"])) * 25.0
        level = "MODERATE"
    elif hum <= h_cfg["high_max"]:
        score = 50.0 + ((hum - h_cfg["moderate_max"]) / (h_cfg["high_max"] - h_cfg["moderate_max"])) * 25.0
        level = "HIGH"
    else:
        score = 75.0 + min(25.0, ((hum - h_cfg["high_max"]) / 15.0) * 25.0)
        level = "CRITICAL"

    return {
        "score": round(float(np.clip(score, 0.0, 100.0)), 2),
        "level": level,
        "value": hum
    }


def get_rainfall_stress(rain_mm: float, rain_prob: float = 0.0) -> Dict[str, Any]:
    """Calculates rainfall stress score (0-100) combining precipitation amount and probability."""
    rain = float(rain_mm)
    prob = float(rain_prob)
    r_cfg = CLIMATE_THRESHOLDS["rainfall"]

    if rain <= r_cfg["low_max"]:
        amount_score = (rain / max(1.0, r_cfg["low_max"])) * 25.0
    elif rain <= r_cfg["moderate_max"]:
        amount_score = 25.0 + ((rain - r_cfg["low_max"]) / (r_cfg["moderate_max"] - r_cfg["low_max"])) * 25.0
    elif rain <= r_cfg["high_max"]:
        amount_score = 50.0 + ((rain - r_cfg["moderate_max"]) / (r_cfg["high_max"] - r_cfg["moderate_max"])) * 25.0
    else:
        amount_score = 75.0 + min(25.0, ((rain - r_cfg["high_max"]) / 20.0) * 25.0)

    combined_score = amount_score * 0.7 + (prob) * 0.3 if prob > 0 else amount_score

    score = float(np.clip(combined_score, 0.0, 100.0))
    if score < 25:
        level = "LOW"
    elif score < 50:
        level = "MODERATE"
    elif score < 75:
        level = "HIGH"
    else:
        level = "CRITICAL"

    return {
        "score": round(score, 2),
        "level": level,
        "value_mm": rain,
        "probability_pct": prob
    }


def get_apparent_temp_stress(temp_c: float, apparent_temp_c: float = None) -> Dict[str, Any]:
    """Calculates heat-index / apparent temperature stress."""
    temp = float(temp_c)
    app_temp = float(apparent_temp_c) if apparent_temp_c is not None else temp + 2.5
    diff = max(0.0, app_temp - temp)

    score = np.clip((app_temp - 25.0) / 20.0 * 100.0, 0.0, 100.0)
    return {
        "score": round(float(score), 2),
        "apparent_temperature": round(app_temp, 1),
        "heat_index_delta": round(diff, 1)
    }


class ClimateRiskEngine:
    """Engine to compute normalized climate features and facility climate risk score."""

    def __init__(self, thresholds: Dict[str, Any] = None):
        self.thresholds = thresholds or CLIMATE_THRESHOLDS

    def extract_climate_features(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts normalized climate features from weather data dictionary."""
        curr_temp = float(weather_data.get("temperature", 28.5))
        curr_hum = float(weather_data.get("humidity", 60.0))
        curr_rain = float(weather_data.get("rain", 0.0))
        rain_prob = float(weather_data.get("rain_probability", 0.0))
        wind_speed = float(weather_data.get("wind", 12.0))
        apparent_temp = weather_data.get("apparent_temperature")

        temp_stress = get_temperature_stress(curr_temp)
        hum_stress = get_humidity_stress(curr_hum)
        rain_stress = get_rainfall_stress(curr_rain, rain_prob)
        app_stress = get_apparent_temp_stress(curr_temp, apparent_temp)

        # Extreme weather score (sustained high heat, heavy rain, or high wind)
        extreme_heat = max(0.0, (curr_temp - 35.0) / 10.0 * 100.0)
        extreme_rain = max(0.0, (curr_rain - 15.0) / 25.0 * 100.0)
        extreme_wind = max(0.0, (wind_speed - 35.0) / 35.0 * 100.0)
        extreme_score = float(np.clip(max(extreme_heat, extreme_rain, extreme_wind), 0.0, 100.0))

        return {
            "temperature_stress": temp_stress["score"],
            "temperature_level": temp_stress["level"],
            "humidity_stress": hum_stress["score"],
            "humidity_level": hum_stress["level"],
            "rainfall_stress": rain_stress["score"],
            "rainfall_level": rain_stress["level"],
            "apparent_temperature_stress": app_stress["score"],
            "apparent_temperature": app_stress["apparent_temperature"],
            "extreme_weather_risk": round(extreme_score, 2),
            "current_metrics": {
                "temperature": curr_temp,
                "humidity": curr_hum,
                "rain": curr_rain,
                "rain_probability": rain_prob,
                "wind": wind_speed
            }
        }

    def calculate_facility_climate_risk(
        self, climate_features: Dict[str, Any], forecast_trend_score: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculates facility-level Climate Risk Score (0-100).
        Weights: Temperature (35%), Humidity (15%), Rainfall (20%), Extreme Weather (20%), Forecast Trend (10%).
        """
        weights = self.thresholds.get("weights", CLIMATE_THRESHOLDS["weights"])

        t_score = float(climate_features.get("temperature_stress", 0.0))
        h_score = float(climate_features.get("humidity_stress", 0.0))
        r_score = float(climate_features.get("rainfall_stress", 0.0))
        e_score = float(climate_features.get("extreme_weather_risk", 0.0))
        tr_score = float(np.clip(forecast_trend_score, 0.0, 100.0))

        risk_score = (
            t_score * weights.get("temperature", 0.35) +
            h_score * weights.get("humidity", 0.15) +
            r_score * weights.get("rainfall", 0.20) +
            e_score * weights.get("extreme_weather", 0.20) +
            tr_score * weights.get("forecast_trend", 0.10)
        )

        risk_score = float(np.clip(risk_score, 0.0, 100.0))
        round_score = round(risk_score, 2)

        if round_score <= 20.0:
            category = "LOW"
        elif round_score <= 40.0:
            category = "MODERATE"
        elif round_score <= 60.0:
            category = "ELEVATED"
        elif round_score <= 80.0:
            category = "HIGH"
        else:
            category = "CRITICAL"

        return {
            "facility_climate_risk": round_score,
            "category": category,
            "breakdown": {
                "temperature_component": round(t_score * weights.get("temperature", 0.35), 2),
                "humidity_component": round(h_score * weights.get("humidity", 0.15), 2),
                "rainfall_component": round(r_score * weights.get("rainfall", 0.20), 2),
                "extreme_weather_component": round(e_score * weights.get("extreme_weather", 0.20), 2),
                "forecast_trend_component": round(tr_score * weights.get("forecast_trend", 0.10), 2)
            }
        }


climate_risk_engine = ClimateRiskEngine()

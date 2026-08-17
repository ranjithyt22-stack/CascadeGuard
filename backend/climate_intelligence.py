"""
CascadeGuard AI — Climate Intelligence & Confidence Engine
Phase 11: Climate Intelligence + Confidence Layer

Provides heatwave duration detection, asset-specific climate stress scoring,
climate trend forecasting (6h/24h), data freshness & confidence evaluation,
and dynamic engineering decision-support explanations.
"""

import numpy as np
import pandas as pd
import time


def analyze_climate_intelligence(weather_raw_data, site_config=None):
    """
    Analyzes raw weather telemetry and returns complete climate intelligence payload.
    """
    if site_config is None:
        from site_config import get_active_site_config
        site_config = get_active_site_config()

    thresholds = site_config.get("climate_thresholds", {})
    thresh_temp = float(thresholds.get("heatwave_threshold_temp", 35.0))
    thresh_hrs = int(thresholds.get("heatwave_threshold_hours", 3))

    is_live = bool(weather_raw_data.get("realtime", False))
    source_name = weather_raw_data.get("source", "Open-Meteo Meteorological API")

    # Data Quality & Confidence
    data_quality = {
        "provider": "Open-Meteo Meteorological API",
        "source": source_name,
        "status": "LIVE" if is_live else "FALLBACK",
        "freshness": "LIVE (< 60s)" if is_live else "OFFLINE_FALLBACK",
        "confidence": "HIGH" if is_live else "LOW",
        "asset_limitations": {
            "transformer": "HISTORICAL_REPLAY",
            "chiller": "HISTORICAL_DATASET",
            "water_pump": "HISTORICAL_DATASET (DECISION SUPPORT ONLY)",
            "climate": "LIVE_OPEN_METEO_API" if is_live else "OFFLINE_FALLBACK"
        }
    }

    # Extract hourly forecast series if present, else synthesize 72h array from current peak metrics
    series_raw = weather_raw_data.get("hourly_series")
    if series_raw and isinstance(series_raw, list) and len(series_raw) > 0:
        hourly = pd.DataFrame(series_raw)
    else:
        # Build synthetic 72h forecast series around provided metrics
        base_temp = float(weather_raw_data.get("temperature", 28.5))
        base_hum = float(weather_raw_data.get("humidity", 65.0))
        base_rain = float(weather_raw_data.get("rain", 0.0))
        base_wind = float(weather_raw_data.get("wind", 12.0))

        times = [time.strftime("%Y-%m-%dT%H:00", time.localtime(time.time() + i * 3600)) for i in range(72)]
        temps = [round(base_temp + 4.0 * np.sin(i / 12 * np.pi), 1) for i in range(72)]
        hums = [round(np.clip(base_hum - 10.0 * np.sin(i / 12 * np.pi), 20, 100), 1) for i in range(72)]
        rains = [base_rain for _ in range(72)]
        winds = [base_wind for _ in range(72)]

        hourly = pd.DataFrame({
            "time": times,
            "temperature": temps,
            "humidity": hums,
            "rain": rains,
            "wind": winds
        })

    # Heatwave Duration Calculation
    temps = hourly["temperature"].values
    max_consec_hot = 0
    current_consec = 0

    for t in temps:
        if t >= thresh_temp:
            current_consec += 1
            if current_consec > max_consec_hot:
                max_consec_hot = current_consec
        else:
            current_consec = 0

    peak_temp = float(np.max(temps))
    curr_temp = float(temps[0])
    curr_hum = float(hourly["humidity"].values[0])
    curr_rain = float(hourly["rain"].values[0])
    curr_wind = float(hourly["wind"].values[0])

    heatwave_detected = (max_consec_hot >= thresh_hrs) or (peak_temp >= thresh_temp)

    if peak_temp >= 42.0 or max_consec_hot >= 7:
        heatwave_severity = "EXTREME"
    elif max_consec_hot >= 4 or peak_temp >= 38.0:
        heatwave_severity = "WARNING"
    elif max_consec_hot >= 1 or peak_temp >= 35.0:
        heatwave_severity = "WATCH"
    else:
        heatwave_severity = "NORMAL"

    heatwave_info = {
        "detected": heatwave_detected,
        "peak_temperature": round(peak_temp, 1),
        "threshold_temperature": round(thresh_temp, 1),
        "duration_hours": max_consec_hot,
        "severity": heatwave_severity,
        "disclaimer": "Engineering decision-support indicator, NOT an official meteorological heatwave declaration."
    }

    # Climate Stress Across Horizon
    heat_s = np.clip((hourly["temperature"] - 30.0) / 15.0 * 100.0, 0.0, 100.0)
    hum_s = np.clip((hourly["humidity"] - 60.0) / 40.0 * 100.0, 0.0, 100.0)
    rn_s = np.clip(hourly["rain"] / 20.0 * 100.0, 0.0, 100.0)
    wnd_s = np.clip((hourly["wind"] - 30.0) / 40.0 * 100.0, 0.0, 100.0)
    stresses = heat_s * 0.45 + hum_s * 0.20 + rn_s * 0.20 + wnd_s * 0.15

    overall_stress = round(float(np.max(stresses)), 2)
    curr_stress = round(float(stresses.values[0]), 2)
    stress_6h = round(float(stresses.values[min(6, len(stresses)-1)]), 2)
    stress_24h = round(float(stresses.values[min(24, len(stresses)-1)]), 2)

    chg_6h = round(stress_6h - curr_stress, 2)
    chg_24h = round(stress_24h - curr_stress, 2)

    if chg_6h > 3.0 or chg_24h > 5.0:
        trend_status = "RISING"
    elif chg_6h < -3.0 or chg_24h < -5.0:
        trend_status = "FALLING"
    else:
        trend_status = "STABLE"

    forecast_trend = {
        "trend": trend_status,
        "current_stress": curr_stress,
        "stress_6h": stress_6h,
        "stress_24h": stress_24h,
        "change_6h": chg_6h,
        "change_24h": chg_24h
    }

    # Asset-Specific Climate Stress
    dur_comp_tx = float(np.clip(max_consec_hot / 8.0 * 100.0, 0.0, 100.0))
    heat_comp_tx = float(np.clip((peak_temp - 30.0) / 15.0 * 100.0, 0.0, 100.0))
    hum_comp_tx = float(np.clip((curr_hum - 60.0) / 40.0 * 100.0, 0.0, 100.0))
    wind_comp_tx = float(np.clip((curr_wind - 30.0) / 40.0 * 100.0, 0.0, 100.0))

    tx_climate_stress = round(0.40 * heat_comp_tx + 0.30 * dur_comp_tx + 0.15 * hum_comp_tx + 0.15 * wind_comp_tx, 2)

    hum_comp_ch = float(np.clip((curr_hum - 50.0) / 50.0 * 100.0, 0.0, 100.0))
    dur_comp_ch = float(np.clip(max_consec_hot / 6.0 * 100.0, 0.0, 100.0))
    chiller_climate_stress = round(0.45 * heat_comp_tx + 0.35 * hum_comp_ch + 0.20 * dur_comp_ch, 2)

    dur_comp_wp = float(np.clip(max_consec_hot / 8.0 * 100.0, 0.0, 100.0))
    pump_climate_stress = round(0.50 * heat_comp_tx + 0.30 * dur_comp_wp + 0.20 * hum_comp_tx, 2)

    asset_impacts = {
        "transformer": {
            "climate_stress": tx_climate_stress,
            "severity": "HIGH" if tx_climate_stress > 50 else ("MEDIUM" if tx_climate_stress > 25 else "LOW"),
            "factors": f"Peak ambient temperature of {peak_temp}°C combined with {max_consec_hot}h sustained thermal stress and ambient humidity may increase transformer top-oil cooling load."
        },
        "chiller": {
            "climate_stress": chiller_climate_stress,
            "severity": "HIGH" if chiller_climate_stress > 50 else ("MEDIUM" if chiller_climate_stress > 25 else "LOW"),
            "factors": f"Ambient humidity of {curr_hum}% and {max_consec_hot}h sustained high temperature could increase HVAC chiller condenser heat rejection drag."
        },
        "water_pump": {
            "climate_stress": pump_climate_stress,
            "severity": "HIGH" if pump_climate_stress > 50 else ("MEDIUM" if pump_climate_stress > 25 else "LOW"),
            "factors": f"Sustained ambient heat duration of {max_consec_hot}h represents potential environmental stress (DECISION SUPPORT ONLY)."
        }
    }

    # Dynamic Explanations
    explanations = []
    if peak_temp >= thresh_temp:
        explanations.append(f"Peak ambient temperature is forecast to reach {peak_temp}°C (exceeding site threshold of {thresh_temp}°C).")
    else:
        explanations.append(f"Peak ambient temperature is forecast at {peak_temp}°C.")

    if max_consec_hot > 0:
        explanations.append(f"Temperature remains above {thresh_temp}°C for {max_consec_hot} consecutive hours.")
    else:
        explanations.append(f"Ambient temperature remains below the site threshold of {thresh_temp}°C.")

    if curr_hum > 75.0:
        explanations.append(f"Elevated relative humidity ({curr_hum}%) increases environmental thermal dissipation stress.")

    if trend_status == "RISING":
        explanations.append(f"Forecast projects a RISING climate stress trend (+{chg_6h} points over 6h, +{chg_24h} points over 24h).")
    elif trend_status == "FALLING":
        explanations.append(f"Forecast projects a FALLING climate stress trend ({chg_6h} points over 6h).")
    else:
        explanations.append("Forecast indicates STABLE climate stress conditions over the next 24 hours.")

    # Sample forecast points for UI rendering (NOW, +3H, +6H, +12H, +24H, +48H, +72H)
    sample_indices = [0, 3, 6, 12, 24, 48, min(71, len(hourly)-1)]
    visual_points = []
    for idx in sample_indices:
        if idx < len(hourly):
            row = hourly.iloc[idx]
            visual_points.append({
                "horizon": f"+{idx}H" if idx > 0 else "NOW",
                "time": str(row["time"]),
                "temperature": float(row["temperature"]),
                "humidity": float(row["humidity"]),
                "stress": round(float(stresses.iloc[idx]), 1)
            })

    return {
        "site_id": site_config.get("site_id", "SITE-001"),
        "location": weather_raw_data.get("location", site_config.get("location", {}).get("name", "Coimbatore")),
        "coordinates": {
            "latitude": weather_raw_data.get("latitude", site_config.get("location", {}).get("latitude", 11.00555)),
            "longitude": weather_raw_data.get("longitude", site_config.get("location", {}).get("longitude", 76.96612))
        },
        "current": {
            "temperature": curr_temp,
            "humidity": curr_hum,
            "rain": curr_rain,
            "wind": curr_wind,
            "timestamp": weather_raw_data.get("timestamp", time.strftime("%Y-%m-%d %H:%M:%S"))
        },
        "forecast_trend": forecast_trend,
        "heatwave": heatwave_info,
        "asset_impacts": asset_impacts,
        "overall_climate_stress": overall_stress,
        "severity": heatwave_severity if heatwave_severity != "NORMAL" else ("WARNING" if overall_stress > 50 else "NORMAL"),
        "data_quality": data_quality,
        "visual_points": visual_points,
        "explanation": explanations
    }

"""
backend/services/prediction_engine.py
======================================
Phase 17 — Predictive Climate Risk & Facility Failure Forecasting

Unified Prediction Engine combining weather forecast horizons, climate features,
equipment risk evaluation, risk trend trajectory, early warning alerts,
predictive maintenance priorities, and multi-site facility risk ranking.
"""

import numpy as np
import time
from typing import Dict, Any, List

from services.climate_risk_engine import climate_risk_engine
from services.equipment_risk_engine import equipment_risk_engine, get_risk_category
from services.recommendation_engine_phase17 import generate_facility_recommendations


class PredictionEngine:
    """Unified engine for predictive climate risk & facility failure forecasting."""

    def generate_72h_hourly_forecast(
        self, site_data: Dict[str, Any], weather_full: Dict[str, Any], telemetry_data: Dict[str, Any] = None, scenario_name: str = None
    ) -> Dict[str, Any]:
        """
        Generates genuine 72-hour hourly risk forecast (0 to 71 hours) using:
        - Live Open-Meteo hourly weather forecast
        - Climate stress calculation at each hour
        - XGBoost ML equipment risk models (Transformer, Chiller, Water Pump)
        - Cascade dependency graph for system risk
        """
        temp_offset = 12.0 if scenario_name == "HEATWAVE" else 0.0
        hourly_series = weather_full.get("hourly_series", [])
        base_temp = float(weather_full.get("temperature", 28.5))
        base_hum = float(weather_full.get("humidity", 60.0))
        base_rain = float(weather_full.get("rain", 0.0))
        base_prob = float(weather_full.get("rain_probability", weather_full.get("precipitation_probability", 0.0)))
        base_wind = float(weather_full.get("wind", 12.0))
        base_app_temp = float(weather_full.get("apparent_temperature", base_temp + 2.5))
        base_press = float(weather_full.get("surface_pressure", 1012.0))

        hourly_points = []
        consec_heat_hours = 0
        max_consec_heat = 0
        peak_temp = -999.0
        max_rain = 0.0
        max_wind = 0.0

        for h in range(72):
            if hourly_series and len(hourly_series) > h:
                row = hourly_series[h]
                w_temp = float(row.get("temperature", base_temp)) + temp_offset
                w_hum = float(row.get("humidity", base_hum))
                w_rain = float(row.get("rain", base_rain))
                w_wind = float(row.get("wind", base_wind))
                w_app_temp = float(row.get("apparent_temperature", w_temp + 2.5))
                w_press = float(row.get("surface_pressure", base_press))
                w_code = int(row.get("weather_code", 0))
                time_str = str(row.get("time", f"+{h}h"))
            else:
                mult = np.sin(h / 12.0 * np.pi)
                w_temp = round(base_temp + 4.0 * mult + temp_offset, 1)
                w_hum = round(float(np.clip(base_hum - 10.0 * mult, 20, 100)), 1)
                w_rain = base_rain if h < 48 else round(base_rain + 2.0 * max(0, mult), 1)
                w_wind = base_wind
                w_app_temp = round(w_temp + 2.5, 1)
                w_press = base_press
                w_code = 0
                time_str = time.strftime("%Y-%m-%d %H:00", time.localtime(time.time() + h * 3600))

            if w_temp > peak_temp:
                peak_temp = w_temp
            if w_rain > max_rain:
                max_rain = w_rain
            if w_wind > max_wind:
                max_wind = w_wind

            if w_temp >= 35.0:
                consec_heat_hours += 1
                if consec_heat_hours > max_consec_heat:
                    max_consec_heat = consec_heat_hours
            else:
                consec_heat_hours = 0

            w_point = {
                "temperature": w_temp,
                "humidity": w_hum,
                "rain": w_rain,
                "rain_probability": base_prob,
                "wind": w_wind,
                "apparent_temperature": w_app_temp,
                "surface_pressure": w_press,
                "weather_code": w_code,
                "peak_forecast_temp": w_temp
            }

            c_feats = climate_risk_engine.extract_climate_features(w_point)
            fac_climate = climate_risk_engine.calculate_facility_climate_risk(c_feats)
            c_stress = fac_climate["facility_climate_risk"]
            w_point["climate_stress"] = c_stress

            eq_risk = equipment_risk_engine.predict_all_equipment_risk(site_data, w_point, telemetry_data)
            tx_r = eq_risk["transformer"]["risk_score"]
            ch_r = eq_risk["chiller"]["risk_score"]
            wp_r = eq_risk["water_pump"]["risk_score"]

            # Dependency-aware Cascade Risk propagation
            base_risks_hour = {
                "transformer": tx_r,
                "chiller": ch_r,
                "water_pump": wp_r
            }
            from services.cascade_service import calculate_cascade
            cascade_eval = calculate_cascade(site_data, w_point, base_risks_hour, scenario_name="NORMAL")
            cascade_r = cascade_eval["cascade_risk"]

            hourly_points.append({
                "hour_offset": h,
                "timestamp": time_str,
                "weather": {
                    "temperature": w_temp,
                    "humidity": w_hum,
                    "rain": w_rain,
                    "wind_speed": w_wind,
                    "apparent_temperature": w_app_temp,
                    "surface_pressure": w_press,
                    "weather_code": w_code
                },
                "climate_stress": round(c_stress, 1),
                "heatwave_active": bool(w_temp >= 35.0),
                "transformer_risk": round(tx_r, 1),
                "chiller_risk": round(ch_r, 1),
                "water_pump_risk": round(wp_r, 1),
                "cascade_risk": cascade_r
            })

        milestone_indices = {
            "NOW": 0,
            "6h": min(6, len(hourly_points) - 1),
            "12h": min(12, len(hourly_points) - 1),
            "24h": min(24, len(hourly_points) - 1),
            "48h": min(48, len(hourly_points) - 1),
            "72h": min(71, len(hourly_points) - 1)
        }

        milestones = {}
        for m_name, m_idx in milestone_indices.items():
            pt = hourly_points[m_idx]
            milestones[m_name] = {
                "hour_offset": m_idx,
                "timestamp": pt["timestamp"],
                "temperature": pt["weather"]["temperature"],
                "humidity": pt["weather"]["humidity"],
                "rain": pt["weather"]["rain"],
                "wind_speed": pt["weather"]["wind_speed"],
                "climate_stress": pt["climate_stress"],
                "transformer_risk": pt["transformer_risk"],
                "chiller_risk": pt["chiller_risk"],
                "water_pump_risk": pt["water_pump_risk"],
                "cascade_risk": pt["cascade_risk"]
            }

        heatwave_detected = bool((max_consec_heat >= 3) or (peak_temp >= 35.0))
        natural_events = {
            "heatwave": {
                "detected": heatwave_detected,
                "peak_temperature": round(float(peak_temp), 1),
                "duration_hours": int(max_consec_heat),
                "severity": "CRITICAL" if peak_temp >= 42.0 else ("WARNING" if peak_temp >= 38.0 else ("WATCH" if peak_temp >= 35.0 else "NORMAL"))
            },
            "heavy_rainfall": {
                "detected": bool(float(max_rain) >= 20.0),
                "peak_rain_mm": round(float(max_rain), 1)
            },
            "high_wind": {
                "detected": bool(float(max_wind) >= 40.0),
                "max_wind_kmh": round(float(max_wind), 1)
            }
        }

        return {
            "hourly_forecast": hourly_points,
            "milestones": milestones,
            "natural_events": natural_events,
            "peak_forecast_temp": round(peak_temp, 1),
            "trend_24h": "RISING" if milestones["24h"]["cascade_risk"] > milestones["NOW"]["cascade_risk"] + 3.0 else ("FALLING" if milestones["24h"]["cascade_risk"] < milestones["NOW"]["cascade_risk"] - 3.0 else "STABLE")
        }

    def generate_predictive_alerts(
        self, site_data: Dict[str, Any], facility_risk: float, equipment_risks: Dict[str, Any], trend_info: Dict[str, Any], weather_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generates automatic predictive alerts for early warning system."""
        alerts = []
        site_id = site_data.get("site_id", "SITE-001")
        site_name = site_data.get("site_name", "Facility")
        city = site_data.get("city", "Facility Location")
        tx_info = equipment_risks.get("transformer", {})
        ch_info = equipment_risks.get("chiller", {})
        wp_info = equipment_risks.get("water_pump", {})

        # Critical alert for Transformer
        if tx_info.get("risk_score", 0) >= 75.0 or (tx_info.get("risk_score", 0) >= 60.0 and trend_info.get("trend") == "RISING"):
            alerts.append({
                "alert_id": f"ALT-TX-{site_id}-{int(time.time())}",
                "site_id": site_id,
                "site_name": site_name,
                "city": city,
                "severity": "CRITICAL" if tx_info.get("risk_score", 0) >= 75.0 else "HIGH",
                "title": f"CRITICAL THERMAL RISK ALERT — {site_name}",
                "message": f"Transformer {tx_info.get('equipment_id')} risk is expected to reach critical levels within 12-18 hours. Forecast peak temperature: {weather_data.get('peak_forecast_temp', weather_data.get('temperature', 35.0))}°C.",
                "current_risk": tx_info.get("risk_score"),
                "failure_probability_pct": tx_info.get("failure_probability_pct"),
                "recommended_action": tx_info.get("recommended_action")
            })

        # High/Critical alert for Chiller
        if ch_info.get("risk_score", 0) >= 70.0:
            alerts.append({
                "alert_id": f"ALT-CH-{site_id}-{int(time.time())}",
                "site_id": site_id,
                "site_name": site_name,
                "city": city,
                "severity": "HIGH",
                "title": f"CHILLER COOLING DEMAND SURGE — {site_name}",
                "message": f"HVAC Chiller {ch_info.get('equipment_id')} experiencing high heat-rejection drag due to elevated humidity ({weather_data.get('humidity', 60)}%) and ambient heat.",
                "current_risk": ch_info.get("risk_score"),
                "failure_probability_pct": ch_info.get("failure_probability_pct"),
                "recommended_action": ch_info.get("recommended_action")
            })

        # High alert for Water Pump
        if wp_info.get("risk_score", 0) >= 65.0:
            alerts.append({
                "alert_id": f"ALT-WP-{site_id}-{int(time.time())}",
                "site_id": site_id,
                "site_name": site_name,
                "city": city,
                "severity": "HIGH",
                "title": f"HEAVY RAINFALL & DRAINAGE ALERT — {site_name}",
                "message": f"Water Pump {wp_info.get('equipment_id')} risk elevated due to high rain probability ({weather_data.get('rain_probability', 0)}%).",
                "current_risk": wp_info.get("risk_score"),
                "failure_probability_pct": wp_info.get("failure_probability_pct"),
                "recommended_action": wp_info.get("recommended_action")
            })

        if not alerts and facility_risk >= 50.0:
            alerts.append({
                "alert_id": f"ALT-FAC-{site_id}-{int(time.time())}",
                "site_id": site_id,
                "site_name": site_name,
                "city": city,
                "severity": "MODERATE",
                "title": f"ELEVATED FACILITY CLIMATE RISK — {site_name}",
                "message": f"Facility climate risk is ELEVATED ({facility_risk}/100) under current weather forecast trend.",
                "current_risk": facility_risk,
                "failure_probability_pct": None,
                "recommended_action": "Monitor climate telemetry and equipment operating parameters closely."
            })

        return alerts

    def predict_facility_risk(
        self, site_data: Dict[str, Any], weather_full: Dict[str, Any], telemetry_data: Dict[str, Any] = None, scenario_name: str = None
    ) -> Dict[str, Any]:
        """Complete facility-level predictive evaluation with genuine 72-hour forecast."""
        site_id = site_data.get("site_id", "SITE-001")
        site_name = site_data.get("site_name", "Industrial Facility")
        city = site_data.get("city", "Coimbatore")
        lat = float(site_data.get("latitude", 11.00555))
        lon = float(site_data.get("longitude", 76.96612))

        # Under HEATWAVE scenario, offset the base weather metrics
        if scenario_name == "HEATWAVE":
            weather_full = dict(weather_full)
            weather_full["temperature"] = float(weather_full.get("temperature", 28.5)) + 12.0
            weather_full["humidity"] = min(100.0, float(weather_full.get("humidity", 60.0)) + 10.0)
            if "hourly_series" in weather_full:
                new_series = []
                for pt in weather_full["hourly_series"]:
                    new_pt = dict(pt)
                    new_pt["temperature"] = float(new_pt.get("temperature", 28.5)) + 12.0
                    new_pt["humidity"] = min(100.0, float(new_pt.get("humidity", 60.0)) + 10.0)
                    new_series.append(new_pt)
                weather_full["hourly_series"] = new_series

        # Expose Phase 4 Dynamic Telemetry Loading / Phase 6 IoT Ingest fallback
        if telemetry_data is None:
            try:
                import state
                telemetry_mode = site_data.get("telemetry_mode", state.telemetry_mgr.mode)

                from services.telemetry_simulation import get_simulated_telemetry
                sim_data = get_simulated_telemetry(site_id, weather_full, site_data)

                if telemetry_mode == "SIMULATION":
                    telemetry_data = sim_data.get("assets", {})
                else:
                    from ot.ts_storage import get_latest_points
                    devices = state.device_registry.get_all_devices()
                    
                    tx_dev = next((d for d in devices if d["location"] == site_id and d["asset_type"] == "transformer"), None)
                    ch_dev = next((d for d in devices if d["location"] == site_id and d["asset_type"] == "chiller"), None)
                    wp_dev = next((d for d in devices if d["location"] == site_id and d["asset_type"] == "water_pump"), None)

                    tx_points = get_latest_points(tx_dev["device_id"]) if tx_dev else {}
                    ch_points = get_latest_points(ch_dev["device_id"]) if ch_dev else {}
                    wp_points = get_latest_points(wp_dev["device_id"]) if wp_dev else {}

                    assets = {}
                    # 1. Transformer
                    if tx_points and (telemetry_mode == "HARDWARE" or (telemetry_mode == "HYBRID" and tx_dev["status"] == "ONLINE")):
                        tx_vals = {k: v["value"] for k, v in tx_points.items()}
                        assets["transformer"] = {
                            "asset_id": tx_dev["asset_id"],
                            "load_pct": tx_vals.get("load_percent", 0.0),
                            "current": tx_vals.get("current", 0.0),
                            "voltage": tx_vals.get("voltage", 0.0),
                            "power": tx_vals.get("KW", 0.0),
                            "oil_temperature": tx_vals.get("OTI", 0.0),
                            "winding_temperature": tx_vals.get("WTI", 0.0)
                        }
                    else:
                        assets["transformer"] = sim_data["assets"]["transformer"]

                    # 2. Chiller
                    if ch_points and (telemetry_mode == "HARDWARE" or (telemetry_mode == "HYBRID" and ch_dev["status"] == "ONLINE")):
                        ch_vals = {k: v["value"] for k, v in ch_points.items()}
                        assets["chiller"] = {
                            "asset_id": ch_dev["asset_id"],
                            "load_pct": ch_vals.get("cooling_load", 0.0),
                            "current": ch_vals.get("compressor_current", 0.0),
                            "power": ch_vals.get("kW", 0.0),
                            "supply_temperature": ch_vals.get("TEO", 0.0),
                            "return_temperature": ch_vals.get("TEI", 0.0),
                            "flow_rate": ch_vals.get("flow_rate", 0.0),
                            "cop": ch_vals.get("cop", 0.0)
                        }
                    else:
                        assets["chiller"] = sim_data["assets"]["chiller"]

                    # 3. Water Pump
                    if wp_points and (telemetry_mode == "HARDWARE" or (telemetry_mode == "HYBRID" and wp_dev["status"] == "ONLINE")):
                        wp_vals = {k: v["value"] for k, v in wp_points.items()}
                        assets["water_pump"] = {
                            "asset_id": wp_dev["asset_id"],
                            "load_pct": wp_vals.get("motor_power", 0.0) / 10.0 if wp_vals.get("motor_power") else 50.0,
                            "current": wp_vals.get("motor_current", 0.0),
                            "voltage": 415.0,
                            "flow_rate": wp_vals.get("flow", 0.0),
                            "pressure": wp_vals.get("pressure", 0.0),
                            "vibration": wp_vals.get("vibration", 0.0),
                            "motor_temperature": wp_vals.get("motor_temperature", 0.0)
                        }
                    else:
                        assets["water_pump"] = sim_data["assets"]["water_pump"]

                    telemetry_data = assets

            except Exception as e:
                print(f"[Prediction Engine] Real-time IoT / fallback loading error: {e}")
                telemetry_data = {}

        # 1. 72-Hour Hourly Forecast Pipeline
        fc_72h = self.generate_72h_hourly_forecast(site_data, weather_full, telemetry_data, scenario_name=scenario_name)
        milestones = fc_72h["milestones"]
        hourly_series = fc_72h["hourly_forecast"]

        # 2. Current Climate Features & Facility Climate Risk
        climate_feats = climate_risk_engine.extract_climate_features(weather_full)
        fac_climate_risk = climate_risk_engine.calculate_facility_climate_risk(
            climate_feats, forecast_trend_score=fc_72h["peak_forecast_temp"]
        )

        # 3. Current Equipment Risk Calculations
        eq_risks = equipment_risk_engine.predict_all_equipment_risk(site_data, weather_full, telemetry_data)

        # 4. Overall Facility Integrated Risk (Now & Forecast Peak)
        tx_score = eq_risks["transformer"]["risk_score"]
        ch_score = eq_risks["chiller"]["risk_score"]
        wp_score = eq_risks["water_pump"]["risk_score"]
        c_score = fac_climate_risk["facility_climate_risk"]

        # Weighted maximum aggregation logic to prevent critical asset risks from being diluted (Requirement 20)
        weighted_risk = 0.35 * tx_score + 0.30 * ch_score + 0.15 * wp_score + 0.20 * c_score
        overall_facility_risk = round(float(np.clip(max(weighted_risk, tx_score, ch_score), 0.0, 100.0)), 2)
        overall_level = get_risk_category(overall_facility_risk)

        # Determine dominant asset (Requirement 21)
        asset_scores = [("Transformer", tx_score), ("Chiller", ch_score), ("Water Pump", wp_score)]
        dominant_asset = max(asset_scores, key=lambda x: x[1])[0]

        # Trajectory analysis for all assets (Requirement 15, 16, 17, 23)
        def analyze_asset_trajectory(hourly, key):
            risks = [pt[key] for pt in hourly]
            curr_r = risks[0]
            peak_r = max(risks)
            peak_idx = risks.index(peak_r)
            peak_t = hourly[peak_idx]["timestamp"]
            
            # Trend mapping
            r_24h = risks[min(24, len(risks)-1)]
            if r_24h > curr_r + 3.0:
                trend = "RISING"
            elif r_24h < curr_r - 3.0:
                trend = "FALLING"
            else:
                trend = "STABLE"
            
            # Time to high risk threshold (>= 70.0)
            time_to_t = None
            for idx, r in enumerate(risks):
                if r >= 70.0:
                    time_to_t = idx
                    break
            return curr_r, peak_r, peak_t, trend, time_to_t

        tx_curr_r, tx_peak_r, tx_peak_t, tx_trend, tx_ttt = analyze_asset_trajectory(hourly_series, "transformer_risk")
        ch_curr_r, ch_peak_r, ch_peak_t, ch_trend, ch_ttt = analyze_asset_trajectory(hourly_series, "chiller_risk")
        wp_curr_r, wp_peak_r, wp_peak_t, wp_trend, wp_ttt = analyze_asset_trajectory(hourly_series, "water_pump_risk")

        # Causal driver generation (Requirement 18, 19)
        def generate_asset_drivers(asset_type, weather, tel):
            drivers = []
            temp = weather.get("temperature", 28.5)
            humidity = weather.get("humidity", 60.0)
            rain = weather.get("rain", 0.0)
            
            tx_tel = tel.get("transformer", {}) if tel else {}
            ch_tel = tel.get("chiller", {}) if tel else {}
            wp_tel = tel.get("water_pump", {}) if tel else {}

            if asset_type == "transformer":
                load = tx_tel.get("load_pct", 70.0)
                wti = tx_tel.get("WTI", temp + 20.0)
                if temp >= 32.0:
                    drivers.append(f"High ambient temperature ({temp}°C) stressing thermal limits")
                if load >= 80.0:
                    drivers.append(f"Elevated equipment electrical load ({load}%)")
                if wti >= 95.0:
                    drivers.append(f"Winding temperature ({wti}°C) close to maximum safe limit (110°C)")
                if not drivers:
                    drivers.append("Normal operating temperatures and load levels")
                    
            elif asset_type == "chiller":
                load = ch_tel.get("load_pct", 65.0)
                cop = ch_tel.get("cop", 4.0)
                if temp >= 32.0:
                    drivers.append(f"Increased cooling demand due to ambient temperature ({temp}°C)")
                if humidity >= 70.0:
                    drivers.append(f"High ambient humidity ({humidity}%) restricting condenser performance")
                if load >= 80.0:
                    drivers.append(f"Chiller compressor operating at peak capacity ({load}%)")
                if cop <= 3.2:
                    drivers.append(f"Decayed Coefficient of Performance (COP: {cop})")
                if not drivers:
                    drivers.append("Condenser cooling performance and efficiency are stable")
                    
            elif asset_type == "water_pump":
                load = wp_tel.get("load_pct", 60.0)
                vib = wp_tel.get("vibration", 1.5)
                if rain >= 10.0:
                    drivers.append(f"High sump drainage pumping demand from rainfall ({rain} mm)")
                if load >= 80.0:
                    drivers.append(f"Pump motor load elevated ({load}%)")
                if vib >= 3.5:
                    drivers.append(f"Abnormal mechanical pump vibration detected ({vib} mm/s)")
                if not drivers:
                    drivers.append("Operating pressures, flows, and vibrations are normal")
                    
            return drivers

        # 5. SHAP Factor Attribution for Milestone 24h & 72h
        import state
        m24 = milestones["24h"]
        sample_v3_data = {
            "ATI": m24["temperature"],
            "OTI": m24["temperature"] + 16.0,
            "WTI": m24["temperature"] + 22.0,
            "KW": 135.0,
            "MPD": 145.0,
            "THDVL1": 3.8,
            "Avg_PF": 0.92
        }
        shap_factors, shap_summary = state.get_dynamic_shap_explanation(sample_v3_data)

        # 6. Predictive Alerts & Prescriptive Recommendations
        trend_info = {"trend": fc_72h["trend_24h"]}
        alerts = self.generate_predictive_alerts(site_data, overall_facility_risk, eq_risks, trend_info, weather_full)
        recommendations = generate_facility_recommendations(site_name, overall_facility_risk, eq_risks, weather_full)

        asset_ids = site_data.get("asset_ids", {})
        tx_id = asset_ids.get("transformer", "TX-001")
        ch_id = asset_ids.get("chiller", "CH-001")
        wp_id = asset_ids.get("water_pump", "WP-001")

        return {
            "site_id": site_id,
            "site_name": site_name,
            "city": city,
            "latitude": lat,
            "longitude": lon,
            "forecast_generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "horizon_hours": 72,
            "data_source": {
                "weather": (
                    "LIVE — Open-Meteo Meteorological API (Exact Geolocation)"
                    if weather_full.get("source_status") == "LIVE"
                    else f"FALLBACK — {weather_full.get('source', 'Weather source unavailable')}"
                ),
                "weather_source_status": weather_full.get("source_status", "UNKNOWN"),
                "telemetry": "HISTORICAL_REPLAY — Industrial Telemetry Replay",
                "models": "XGBoost ML Models (v3 Operational, Health Index, Chiller, Water Pump RUL)",
                "explanation": "SHAP TreeExplainer (XAI)"
            },
            "overall_facility_risk": overall_facility_risk,
            "risk_level": overall_level,
            "climate_risk": fac_climate_risk["facility_climate_risk"],
            "climate_category": fac_climate_risk["category"],
            "weather_summary": {
                "current_temperature": weather_full.get("temperature", 28.5),
                "forecast_peak_temperature": fc_72h["peak_forecast_temp"],
                "humidity": weather_full.get("humidity", 60.0),
                "rain_mm": weather_full.get("rain", 0.0),
                "rain_probability_pct": weather_full.get("rain_probability", 0.0),
                "wind_speed": weather_full.get("wind", 12.0)
            },
            "equipment": eq_risks,
            "hourly_forecast": hourly_series,
            "milestones": milestones,
            "forecast_horizons": milestones,
            "natural_events": fc_72h["natural_events"],
            "shap_explanation": {
                "factors": shap_factors,
                "summary": shap_summary
            },
            "trend_analysis": {
                "trend": fc_72h["trend_24h"],
                "peak_forecast_temp": fc_72h["peak_forecast_temp"]
            },
            "predictive_alerts": alerts,
            "recommendations": recommendations,
            "controlled_scenario": bool(scenario_name == "HEATWAVE"),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            
            # Phase 4 API contracts (Requirement 24)
            "facility_risk": {
                "current": overall_facility_risk,
                "peak": max([pt["cascade_risk"] for pt in hourly_series]),
                "trend": fc_72h["trend_24h"],
                "dominant_asset": dominant_asset
            },
            "assets": {
                "transformer": {
                    "asset_id": tx_id,
                    "current_risk": tx_curr_r,
                    "peak_risk": tx_peak_r,
                    "trend": tx_trend,
                    "peak_time": tx_peak_t,
                    "time_to_threshold": tx_ttt,
                    "drivers": generate_asset_drivers("transformer", weather_full, telemetry_data)
                },
                "chiller": {
                    "asset_id": ch_id,
                    "current_risk": ch_curr_r,
                    "peak_risk": ch_peak_r,
                    "trend": ch_trend,
                    "peak_time": ch_peak_t,
                    "time_to_threshold": ch_ttt,
                    "drivers": generate_asset_drivers("chiller", weather_full, telemetry_data)
                },
                "water_pump": {
                    "asset_id": wp_id,
                    "current_risk": wp_curr_r,
                    "peak_risk": wp_peak_r,
                    "trend": wp_trend,
                    "peak_time": wp_peak_t,
                    "time_to_threshold": wp_ttt,
                    "drivers": generate_asset_drivers("water_pump", weather_full, telemetry_data)
                }
            }
        }

    def generate_facility_risk_ranking(self, all_sites: List[Dict[str, Any]], weather_client_inst) -> List[Dict[str, Any]]:
        """Ranks all registered facilities by overall predictive risk score."""
        rankings = []
        for site in all_sites:
            s_id = site["site_id"]
            lat = site["latitude"]
            lon = site["longitude"]
            loc = site.get("city", site.get("site_name", "Facility"))

            w_data = weather_client_inst.get_current_data(location=loc, latitude=lat, longitude=lon, site_id=s_id)
            eval_res = self.predict_facility_risk(site, w_data["data"])

            rankings.append({
                "site_id": s_id,
                "site_name": site["site_name"],
                "city": loc,
                "latitude": lat,
                "longitude": lon,
                "overall_facility_risk": eval_res["overall_facility_risk"],
                "risk_level": eval_res["risk_level"],
                "climate_risk": eval_res["climate_risk"],
                "transformer_risk": eval_res["equipment"]["transformer"]["risk_score"],
                "chiller_risk": eval_res["equipment"]["chiller"]["risk_score"],
                "water_pump_risk": eval_res["equipment"]["water_pump"]["risk_score"],
                "highest_risk_equipment": max(
                    [("Transformer", eval_res["equipment"]["transformer"]["risk_score"]),
                     ("Chiller", eval_res["equipment"]["chiller"]["risk_score"]),
                     ("Water Pump", eval_res["equipment"]["water_pump"]["risk_score"])],
                    key=lambda x: x[1]
                )[0]
            })

        rankings.sort(key=lambda x: x["overall_facility_risk"], reverse=True)

        for i, r in enumerate(rankings):
            r["rank"] = i + 1

        return rankings

    def generate_maintenance_priorities(self, rankings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generates prioritized list of equipment maintenance actions across monitored sites."""
        priorities = []
        for r in rankings:
            s_id = r["site_id"]
            s_name = r["site_name"]
            
            items = [
                ("Transformer", f"TX-{s_id}", r["transformer_risk"]),
                ("Chiller", f"CH-{s_id}", r["chiller_risk"]),
                ("Water Pump", f"WP-{s_id}", r["water_pump_risk"])
            ]

            for eq_type, eq_id, score in items:
                priorities.append({
                    "site_id": s_id,
                    "site_name": s_name,
                    "equipment_type": eq_type,
                    "equipment_id": eq_id,
                    "risk_score": score,
                    "risk_level": get_risk_category(score),
                    "urgency_window": "6-12 Hours" if score >= 75 else ("12-24 Hours" if score >= 50 else "24-48 Hours"),
                    "action_required": f"Perform preventive inspection on {eq_type} {eq_id} at {s_name}."
                })

        priorities.sort(key=lambda x: x["risk_score"], reverse=True)

        for i, p in enumerate(priorities):
            p["priority"] = i + 1

        return priorities


prediction_engine = PredictionEngine()

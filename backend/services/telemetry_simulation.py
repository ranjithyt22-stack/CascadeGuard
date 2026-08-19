"""
backend/services/telemetry_simulation.py
=========================================
Phase 3 — Realistic Asset Telemetry & Equipment State Simulation Engine.
Generates deterministic, physically plausible telemetry for Transformer, Chiller,
and Water Pump assets based on ambient weather and facility load conditions.
"""
import time
import numpy as np

def get_simulated_telemetry(site_id: str, weather_raw: dict, site_info: dict) -> dict:
    """
    Computes deterministic telemetry variables influenced by actual facility coordinates weather.
    Ensures physically plausible cross-variable constraints and resolves asset risk scores.
    """
    from services.equipment_risk_engine import equipment_risk_engine

    # Extract weather inputs
    curr_temp = float(weather_raw.get("temperature", 28.5))
    humidity = float(weather_raw.get("humidity", 60.0))
    rain = float(weather_raw.get("rain", 0.0))
    wind = float(weather_raw.get("wind", 12.0))
    climate_stress = float(weather_raw.get("climate_stress", 30.0))

    # Determine base load multiplier using a deterministic time-of-day sine wave
    # to avoid random jumps while keeping it dynamic
    hour_val = float(time.localtime().tm_hour)
    load_mult = 1.0 + 0.15 * np.sin((hour_val - 8.0) / 12.0 * np.pi)

    # 1. TRANSFORMER
    tx_id = site_info.get("transformer_id") or "TX-001"
    tx_load_pct = round(float(np.clip((65.0 + (curr_temp - 25.0) * 0.8) * load_mult, 40.0, 95.0)), 1)
    tx_current = round(float(tx_load_pct * 12.5), 1)
    tx_voltage = round(float(11.0 + 0.05 * np.sin(hour_val / 3.0)), 2)
    tx_power = round(float(tx_load_pct * 15.2), 1)
    tx_oil_temp = round(float(curr_temp + (tx_load_pct / 100.0) * 45.0 + 2.0 * np.cos(hour_val / 4.0)), 1)
    tx_winding_temp = round(float(tx_oil_temp + (tx_load_pct / 100.0) * 12.0 + 1.0 * np.sin(hour_val / 2.0)), 1)

    tx_telemetry = {
        "OTI": tx_oil_temp,
        "WTI": tx_winding_temp,
        "ATI": curr_temp,
        "VL1": tx_voltage,
        "VL2": tx_voltage,
        "VL3": tx_voltage,
        "IL1": tx_current,
        "IL2": tx_current,
        "IL3": tx_current,
        "KW": tx_power
    }

    # 2. CHILLER
    ch_id = site_info.get("chiller_id") or "CH-001"
    ch_load_pct = round(float(np.clip((50.0 + (curr_temp - 25.0) * 1.5 + (humidity - 50.0) * 0.4) * load_mult, 30.0, 95.0)), 1)
    ch_current = round(float(ch_load_pct * 3.8), 1)
    ch_power = round(float(ch_load_pct * 4.4), 1)
    ch_supply_temp = round(float(6.5 + 0.3 * np.sin(hour_val / 5.0)), 1)
    ch_return_temp = round(float(ch_supply_temp + (ch_load_pct / 100.0) * 5.8), 1)
    ch_flow_rate = round(float(120.0 + 15.0 * np.cos(hour_val / 6.0)), 1)
    ch_cop = round(float(np.clip(4.8 - (curr_temp - 20.0) * 0.05 - (ch_load_pct / 100.0) * 0.8, 1.5, 6.0)), 2)

    ch_telemetry = {
        "TEI": ch_return_temp,
        "TEO": ch_supply_temp,
        "TCI": curr_temp + 2.0,
        "TCO": curr_temp + 2.0 + (ch_load_pct / 100.0) * 8.0,
        "kW": ch_power
    }

    # 3. WATER PUMP
    wp_id = site_info.get("water_pump_id") or "WP-001"
    wp_load_pct = round(float(np.clip((55.0 + rain * 2.2) * load_mult, 35.0, 90.0)), 1)
    wp_current = round(float(wp_load_pct * 1.9), 1)
    wp_voltage = round(float(415.0 + 3.0 * np.sin(hour_val / 2.0)), 1)
    wp_flow_rate = round(float(np.clip(125.0 - (wp_load_pct - 55.0) * 0.2, 50.0, 160.0)), 1)
    wp_pressure = round(float(np.clip(4.2 - (wp_flow_rate - 125.0) * 0.012, 1.5, 6.0)), 2)
    wp_vibration = round(float(np.clip(1.5 + (wp_load_pct / 100.0) * 1.8 + (0.5 if rain > 5.0 else 0.0), 0.5, 8.0)), 2)
    wp_motor_temp = round(float(48.0 + (wp_load_pct / 100.0) * 16.0 + (curr_temp - 25.0) * 0.3), 1)

    wp_telemetry = {
        "flow": wp_flow_rate,
        "pressure": wp_pressure,
        "vibration": wp_vibration,
        "motor_temperature": wp_motor_temp
    }

    # Run predictor models to get actual deterministic risk scores
    # This fulfills: Connect telemetry to existing prediction
    tx_res = equipment_risk_engine.transformer_predictor.predict_risk(tx_id, weather_raw, tx_telemetry)
    ch_res = equipment_risk_engine.chiller_predictor.predict_risk(ch_id, weather_raw, ch_telemetry)
    wp_res = equipment_risk_engine.water_pump_predictor.predict_risk(wp_id, weather_raw, wp_telemetry)

    tx_risk = tx_res["risk_score"]
    ch_risk = ch_res["risk_score"]
    wp_risk = wp_res["risk_score"]

    return {
        "site_id": site_id,
        "site_name": site_info.get("site_name"),
        "telemetry_source": "SIMULATED",
        "telemetry_status": "SIMULATED",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "assets": {
            "transformer": {
                "asset_id": tx_id,
                "load_pct": tx_load_pct,
                "current": tx_current,
                "voltage": tx_voltage,
                "power": tx_power,
                "oil_temperature": tx_oil_temp,
                "winding_temperature": tx_winding_temp,
                "health": round(100.0 - tx_risk, 1),
                "risk": tx_risk
            },
            "chiller": {
                "asset_id": ch_id,
                "load_pct": ch_load_pct,
                "current": ch_current,
                "power": ch_power,
                "supply_temperature": ch_supply_temp,
                "return_temperature": ch_return_temp,
                "flow_rate": ch_flow_rate,
                "cop": ch_cop,
                "health": round(100.0 - ch_risk, 1),
                "risk": ch_risk
            },
            "water_pump": {
                "asset_id": wp_id,
                "load_pct": wp_load_pct,
                "current": wp_current,
                "voltage": wp_voltage,
                "flow_rate": wp_flow_rate,
                "pressure": wp_pressure,
                "vibration": wp_vibration,
                "motor_temperature": wp_motor_temp,
                "health": round(100.0 - wp_risk, 1),
                "risk": wp_risk
            }
        }
    }

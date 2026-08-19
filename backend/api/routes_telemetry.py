"""
backend/api/routes_telemetry.py
================================
Phase 12: Industrial OT Connectivity endpoints
- GET  /api/telemetry/status
- GET  /api/telemetry/live
- POST /api/telemetry/mode
- POST /api/telemetry/scenario
- GET  /api/telemetry/asset/{asset_id}
"""
import time
from fastapi import APIRouter, Path, HTTPException, Body

import state
from schemas.requests import TelemetryModeRequest, TelemetryScenarioRequest

router = APIRouter()


@router.get("/telemetry/status")
def telemetry_status_endpoint():
    return {
        "success": True,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "telemetry_mode": state.telemetry_mgr.mode,
        "active_scenario": state.telemetry_mgr.active_scenario,
        "assets": state.telemetry_mgr.get_status()
    }


@router.get("/telemetry/live")
def telemetry_live_endpoint():
    return {
        "success": True,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "telemetry_mode": state.telemetry_mgr.mode,
        "active_scenario": state.telemetry_mgr.active_scenario,
        "telemetry": state.telemetry_mgr.get_all_live_telemetry()
    }


@router.post("/telemetry/mode")
def telemetry_mode_endpoint(body: TelemetryModeRequest):
    try:
        req_mode = body.mode
        if not req_mode:
            raise HTTPException(status_code=400, detail="Missing required parameter: mode")
        is_ok = state.telemetry_mgr.set_mode(req_mode)
        if not is_ok:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid telemetry mode '{req_mode}'. Allowed values: ['MOCK', 'REAL_OT']"
            )
        return {
            "success": True,
            "telemetry_mode": state.telemetry_mgr.mode,
            "status": state.telemetry_mgr.get_status()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/facilities/{site_id}/telemetry-mode")
def post_facility_telemetry_mode(site_id: str = Path(...), body: TelemetryModeRequest = Body(...)):
    site = state.site_registry.get_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail=f"Site '{site_id}' not found.")
    
    req_mode = body.mode.upper()
    if req_mode not in ["SIMULATION", "HARDWARE", "HYBRID"]:
        raise HTTPException(status_code=400, detail="Allowed modes: ['SIMULATION', 'HARDWARE', 'HYBRID']")
        
    site["telemetry_mode"] = req_mode
    state.site_registry.update_site(site_id, site)
    return {"success": True, "telemetry_mode": req_mode}


@router.post("/telemetry/scenario")
def telemetry_scenario_endpoint(body: TelemetryScenarioRequest):
    try:
        req_scenario = body.scenario
        if not req_scenario:
            raise HTTPException(status_code=400, detail="Missing required parameter: scenario")
        is_ok = state.telemetry_mgr.set_scenario(req_scenario)
        if not is_ok:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid scenario '{req_scenario}'. Allowed values: ['NORMAL', 'HIGH_LOAD', 'HEAT_STRESS', 'CHILLER_OVERLOAD', 'PUMP_DEGRADATION', 'COMBINED_CASCADE']"
            )
        return {
            "success": True,
            "active_scenario": state.telemetry_mgr.active_scenario,
            "live_telemetry": state.telemetry_mgr.get_all_live_telemetry()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/telemetry/asset/{asset_id}")
def telemetry_single_asset_endpoint(asset_id: str = Path(...)):
    try:
        aid = str(asset_id).upper()
        category = "transformer"
        if "CH" in aid:
            category = "chiller"
        elif "WP" in aid or "PUMP" in aid:
            category = "water_pump"
        data = state.telemetry_mgr.get_asset_telemetry(category, aid)
        return {
            "success": True,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "telemetry": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from fastapi import Query
from pydantic import BaseModel

class HttpTelemetryPayload(BaseModel):
    device_id: str
    asset_id: str
    asset_type: str
    timestamp: str = None
    sequence: int = None
    source: str = "hardware"
    measurements: dict

@router.post("/v1/telemetry")
def post_v1_telemetry(payload: HttpTelemetryPayload):
    try:
        site_id = "CBE-001"
        dev = state.device_registry.get_device(payload.device_id)
        if dev:
            site_id = dev["location"]
            
        from ot.mqtt_client import CascadeGuardMQTTClient
        client_inst = CascadeGuardMQTTClient(state.device_registry)
        client_inst.is_connected = True
        client_inst.process_raw_telemetry(site_id, payload.asset_type, payload.device_id, payload.dict())
        
        return {"success": True, "message": "Telemetry point ingested successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/v1/devices")
def get_v1_devices():
    return {
        "success": True,
        "count": len(state.device_registry.get_all_devices()),
        "devices": state.device_registry.get_all_devices()
    }


@router.get("/v1/devices/{device_id}")
def get_v1_device_by_id(device_id: str = Path(...)):
    dev = state.device_registry.get_device(device_id)
    if not dev:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found.")
    return {"success": True, "device": dev}

@router.get("/v1/devices/{device_id}/telemetry")
def get_v1_device_telemetry(device_id: str = Path(...), measurement: str = Query(...), limit: int = Query(50)):
    from ot.ts_storage import get_historical_series
    history = get_historical_series(device_id, measurement, limit=limit)
    return {
        "success": True,
        "device_id": device_id,
        "measurement": measurement,
        "count": len(history),
        "history": history
    }

@router.get("/v1/devices/{device_id}/health")
def get_v1_device_health(device_id: str = Path(...)):
    dev = state.device_registry.get_device(device_id)
    if not dev:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found.")
    return {
        "success": True,
        "device_id": device_id,
        "status": dev.get("status", "OFFLINE"),
        "last_seen": dev.get("last_seen", ""),
        "signal_quality": dev.get("signal_quality", 100),
        "battery_status": "OK"
    }

@router.get("/v1/telemetry/latest")
def get_v1_telemetry_latest(device_id: str = Query(...)):
    from ot.ts_storage import get_latest_points
    latest = get_latest_points(device_id)
    return {
        "success": True,
        "device_id": device_id,
        "latest": latest
    }

@router.get("/v1/telemetry/history")
def get_v1_telemetry_history(device_id: str = Query(...), measurement: str = Query(...), limit: int = Query(100)):
    from ot.ts_storage import get_historical_series
    history = get_historical_series(device_id, measurement, limit=limit)
    return {
        "success": True,
        "device_id": device_id,
        "measurement": measurement,
        "count": len(history),
        "history": history
    }

@router.get("/facilities/{site_id}/telemetry")
def get_facility_telemetry_endpoint(site_id: str = Path(...)):
    try:
        site_info = state.site_registry.get_site(site_id)
        if not site_info:
            raise HTTPException(status_code=404, detail=f"Site '{site_id}' not found.")
        
        telemetry_mode = site_info.get("telemetry_mode", state.telemetry_mgr.mode)

        lat = site_info.get("latitude")
        lon = site_info.get("longitude")
        city = site_info.get("city") or site_info.get("site_name")
        
        w_norm = state.weather_client_inst.get_current_data(
            location=city, latitude=lat, longitude=lon, site_id=site_id
        )
        weather_raw = w_norm.get("data", {})
        
        from services.telemetry_simulation import get_simulated_telemetry
        sim_data = get_simulated_telemetry(site_id, weather_raw, site_info)

        if telemetry_mode == "SIMULATION":
            return {
                "success": True,
                "telemetry": sim_data
            }

        from ot.ts_storage import get_latest_points
        from ot.device_registry import DeviceRegistry
        
        registry = state.device_registry
        devices = registry.get_all_devices()
        
        tx_dev = next((d for d in devices if d["location"] == site_id and d["asset_type"] == "transformer"), None)
        ch_dev = next((d for d in devices if d["location"] == site_id and d["asset_type"] == "chiller"), None)
        wp_dev = next((d for d in devices if d["location"] == site_id and d["asset_type"] == "water_pump"), None)
        env_dev = next((d for d in devices if d["location"] == site_id and d["asset_type"] == "environment"), None)

        tx_points = get_latest_points(tx_dev["device_id"]) if tx_dev else {}
        ch_points = get_latest_points(ch_dev["device_id"]) if ch_dev else {}
        wp_points = get_latest_points(wp_dev["device_id"]) if wp_dev else {}
        env_points = get_latest_points(env_dev["device_id"]) if env_dev else {}

        from ot.providers import EnvironmentDataProvider
        local_env = {k: v["value"] for k, v in env_points.items()}
        merged_weather = EnvironmentDataProvider.get_merged_weather(site_id, weather_raw, local_env)

        assets = {}

        if tx_points and (telemetry_mode == "HARDWARE" or (telemetry_mode == "HYBRID" and tx_dev["status"] == "ONLINE")):
            from services.equipment_risk_engine import equipment_risk_engine
            tx_data_vals = {k: v["value"] for k, v in tx_points.items()}
            tx_res = equipment_risk_engine.transformer_predictor.predict_risk(site_info.get("transformer_id", "TX-001"), merged_weather, tx_data_vals)
            tx_risk = tx_res["risk_score"]
            
            assets["transformer"] = {
                "asset_id": tx_dev["asset_id"],
                "load_pct": tx_data_vals.get("load_percent", 0.0),
                "current": tx_data_vals.get("current", 0.0),
                "voltage": tx_data_vals.get("voltage", 0.0),
                "power": tx_data_vals.get("KW", 0.0),
                "oil_temperature": tx_data_vals.get("OTI", 0.0),
                "winding_temperature": tx_data_vals.get("WTI", 0.0),
                "health": round(100.0 - tx_risk, 1),
                "risk": tx_risk,
                "source": "HARDWARE",
                "device_id": tx_dev["device_id"],
                "connection": tx_dev["status"]
            }
        else:
            assets["transformer"] = {
                **sim_data["assets"]["transformer"],
                "source": "SIMULATION",
                "device_id": tx_dev["device_id"] if tx_dev else "TRF-001",
                "connection": tx_dev["status"] if tx_dev else "SIMULATED"
            }

        if ch_points and (telemetry_mode == "HARDWARE" or (telemetry_mode == "HYBRID" and ch_dev["status"] == "ONLINE")):
            from services.equipment_risk_engine import equipment_risk_engine
            ch_data_vals = {k: v["value"] for k, v in ch_points.items()}
            ch_res = equipment_risk_engine.chiller_predictor.predict_risk(site_info.get("chiller_id", "CH-001"), merged_weather, ch_data_vals)
            ch_risk = ch_res["risk_score"]
            
            assets["chiller"] = {
                "asset_id": ch_dev["asset_id"],
                "load_pct": ch_data_vals.get("cooling_load", 0.0),
                "current": ch_data_vals.get("compressor_current", 0.0),
                "power": ch_data_vals.get("kW", 0.0),
                "supply_temperature": ch_data_vals.get("TEO", 0.0),
                "return_temperature": ch_data_vals.get("TEI", 0.0),
                "flow_rate": ch_data_vals.get("flow_rate", 0.0),
                "cop": ch_data_vals.get("cop", 0.0),
                "health": round(100.0 - ch_risk, 1),
                "risk": ch_risk,
                "source": "HARDWARE",
                "device_id": ch_dev["device_id"],
                "connection": ch_dev["status"]
            }
        else:
            assets["chiller"] = {
                **sim_data["assets"]["chiller"],
                "source": "SIMULATION",
                "device_id": ch_dev["device_id"] if ch_dev else "CHL-001",
                "connection": ch_dev["status"] if ch_dev else "SIMULATED"
            }

        if wp_points and (telemetry_mode == "HARDWARE" or (telemetry_mode == "HYBRID" and wp_dev["status"] == "ONLINE")):
            from services.equipment_risk_engine import equipment_risk_engine
            wp_data_vals = {k: v["value"] for k, v in wp_points.items()}
            wp_res = equipment_risk_engine.water_pump_predictor.predict_risk(site_info.get("water_pump_id", "WP-001"), merged_weather, wp_data_vals)
            wp_risk = wp_res["risk_score"]
            
            assets["water_pump"] = {
                "asset_id": wp_dev["asset_id"],
                "load_pct": wp_data_vals.get("motor_power", 0.0) / 10.0 if wp_data_vals.get("motor_power") else 50.0,
                "current": wp_data_vals.get("motor_current", 0.0),
                "voltage": 415.0,
                "flow_rate": wp_data_vals.get("flow", 0.0),
                "pressure": wp_data_vals.get("pressure", 0.0),
                "vibration": wp_data_vals.get("vibration", 0.0),
                "motor_temperature": wp_data_vals.get("motor_temperature", 0.0),
                "health": round(100.0 - wp_risk, 1),
                "risk": wp_risk,
                "source": "HARDWARE",
                "device_id": wp_dev["device_id"],
                "connection": wp_dev["status"]
            }
        else:
            assets["water_pump"] = {
                **sim_data["assets"]["water_pump"],
                "source": "SIMULATION",
                "device_id": wp_dev["device_id"] if wp_dev else "PMP-001",
                "connection": wp_dev["status"] if wp_dev else "SIMULATED"
            }

        return {
            "success": True,
            "telemetry": {
                "site_id": site_id,
                "site_name": site_info.get("site_name"),
                "telemetry_source": telemetry_mode,
                "telemetry_status": "HYBRID" if telemetry_mode == "HYBRID" else "LIVE",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "assets": assets,
                "environment_source": merged_weather["source"],
                "discrepancy": merged_weather["discrepancy"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


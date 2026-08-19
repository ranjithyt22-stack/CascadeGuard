"""
backend/api/routes_climate.py
==============================
Phase 11, 14 & 15: Climate & Weather Endpoints
- GET /api/weather (Normalized KMCH Open-Meteo weather response)
- GET /api/climate-intelligence
- GET /api/climate
"""
import os
import time
import requests
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

import state
from climate_intelligence import analyze_climate_intelligence
from site_registry import validate_coordinates

router = APIRouter()

OPEN_METEO_BASE_URL = os.environ.get("OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1/forecast")
KMCH_LAT = float(os.environ.get("LATITUDE", 11.0168))
KMCH_LON = float(os.environ.get("LONGITUDE", 76.9558))
KMCH_TZ = os.environ.get("TIMEZONE", "Asia/Kolkata")


@router.get("/weather")
def get_weather_endpoint(
    latitude: float = Query(None),
    longitude: float = Query(None),
    forecast_days: int = Query(3)
):
    try:
        lat = latitude if latitude is not None else KMCH_LAT
        lon = longitude if longitude is not None else KMCH_LON

        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,precipitation_probability,wind_speed_10m,surface_pressure",
            "forecast_days": forecast_days,
            "timezone": KMCH_TZ
        }

        resp = requests.get(OPEN_METEO_BASE_URL, params=params, timeout=10)
        data = resp.json()

        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        humids = hourly.get("relative_humidity_2m", [])
        precips = hourly.get("precipitation", [])
        precip_probs = hourly.get("precipitation_probability", [])
        winds = hourly.get("wind_speed_10m", [])
        pressures = hourly.get("surface_pressure", [])

        current = {}
        forecast = []

        if times:
            current = {
                "time": times[0],
                "temperature_2m": temps[0] if temps else None,
                "relative_humidity_2m": humids[0] if humids else None,
                "precipitation": precips[0] if precips else None,
                "precipitation_probability": precip_probs[0] if precip_probs else None,
                "wind_speed_10m": winds[0] if winds else None,
                "surface_pressure": pressures[0] if pressures else None
            }

            for idx in range(len(times)):
                forecast.append({
                    "time": times[idx],
                    "temperature_2m": temps[idx] if idx < len(temps) else None,
                    "relative_humidity_2m": humids[idx] if idx < len(humids) else None,
                    "precipitation": precips[idx] if idx < len(precips) else None,
                    "precipitation_probability": precip_probs[idx] if idx < len(precip_probs) else None,
                    "wind_speed_10m": winds[idx] if idx < len(winds) else None,
                    "surface_pressure": pressures[idx] if idx < len(pressures) else None
                })

        payload = {
            "facility": {
                "name": os.environ.get("FACILITY_NAME", "KMCH"),
                "city": os.environ.get("FACILITY_CITY", "Coimbatore"),
                "state": os.environ.get("FACILITY_STATE", "Tamil Nadu"),
                "country": os.environ.get("FACILITY_COUNTRY", "India")
            },
            "location": {
                "latitude": lat,
                "longitude": lon,
                "timezone": KMCH_TZ
            },
            "current": current,
            "forecast": forecast,
            "source": "Open-Meteo"
        }
        return payload
    except Exception as e:
        import traceback; traceback.print_exc()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@router.get("/climate-intelligence")
@router.get("/climate")
def climate_intelligence_endpoint(
    site_id: str = Query(None),
    location: str = Query(None),
    latitude: float = Query(None),
    longitude: float = Query(None)
):
    try:
        if latitude is not None and longitude is not None:
            is_valid, err_msg = validate_coordinates(latitude, longitude)
            if not is_valid:
                return JSONResponse(status_code=400, content={"success": False, "error": err_msg})

        site_info = None
        if site_id:
            site_info = state.site_registry.get_site(site_id)
            if not site_info:
                return JSONResponse(status_code=404, content={"success": False, "error": f"Site '{site_id}' not found"})
            latitude = site_info.get("latitude")
            longitude = site_info.get("longitude")
            location = site_info.get("city") or site_info.get("site_name")

        if latitude is None or longitude is None:
            s1 = state.site_registry.get_site("SITE-001") or {}
            site_info = s1
            latitude = s1.get("latitude", KMCH_LAT)
            longitude = s1.get("longitude", KMCH_LON)
            location = location or s1.get("city", "Coimbatore")
            site_id = "SITE-001"

        w_norm = state.weather_client_inst.get_current_data(
            location=location, latitude=latitude, longitude=longitude, site_id=site_id or "SITE-001"
        )
        raw_weather = w_norm["data"]
        intel = analyze_climate_intelligence(raw_weather, site_info or {"site_id": site_id, "location": {"name": location, "latitude": latitude, "longitude": longitude}})

        if site_info:
            intel["site_id"] = site_info.get("site_id")
            intel["site_name"] = site_info.get("site_name")
            intel["city"] = site_info.get("city", location)
            intel["latitude"] = site_info.get("latitude", latitude)
            intel["longitude"] = site_info.get("longitude", longitude)

        return {
            "success": True,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "climate_intelligence": intel
        }
    except Exception as e:
        import traceback; traceback.print_exc()
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


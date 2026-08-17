"""
CascadeGuard AI — Real-Time Weather & Climate API Client
Phase 10: Real API Integration & Live Data Adapter Architecture

Connects to the Open-Meteo Weather REST API to retrieve real-time weather and forecast data.
Includes 5-minute memory caching, coordinate-based weather retrieval, automatic geocoding, error handling, and offline fallback.
"""

import time
import requests
import pandas as pd
import numpy as np
from api_clients.schema import normalize_asset_telemetry, calculate_data_freshness

WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1/search"

_WEATHER_CACHE = {}


class WeatherAPIClient:
    def __init__(self):
        self.provider = "Open-Meteo Meteorological API"
        self.official_url = "https://open-meteo.com"
        self.source_name = "live_open_meteo_api"

    def get_source(self):
        return self.source_name

    def is_available(self):
        return True

    def get_status(self):
        return {
            "provider": self.provider,
            "status": "LIVE_API_ONLINE",
            "source": self.source_name,
            "realtime_available": True
        }

    def get_weather_by_coordinates(self, latitude, longitude, location_name="Custom Site"):
        cache_key = f"{round(float(latitude), 4)}_{round(float(longitude), 4)}"
        now = time.time()
        if cache_key in _WEATHER_CACHE:
            entry = _WEATHER_CACHE[cache_key]
            if now - entry["time"] < 300:  # 5-minute cache
                return entry["data"]

        try:
            w_params = {
                "latitude": float(latitude),
                "longitude": float(longitude),
                "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
                "forecast_days": 3,
                "timezone": "auto"
            }
            res_w = requests.get(WEATHER_API_URL, params=w_params, timeout=4)
            weather = res_w.json()

            if "hourly" in weather and "temperature_2m" in weather["hourly"]:
                df = pd.DataFrame({
                    "time": weather["hourly"]["time"],
                    "temperature": weather["hourly"]["temperature_2m"],
                    "humidity": weather["hourly"]["relative_humidity_2m"],
                    "rain": weather["hourly"]["precipitation"],
                    "wind": weather["hourly"]["wind_speed_10m"]
                })

                heat = np.clip((df["temperature"] - 30.0) / 15.0 * 100.0, 0.0, 100.0)
                hum = np.clip((df["humidity"] - 60.0) / 40.0 * 100.0, 0.0, 100.0)
                rn = np.clip(df["rain"] / 20.0 * 100.0, 0.0, 100.0)
                wnd = np.clip((df["wind"] - 30.0) / 40.0 * 100.0, 0.0, 100.0)
                df["climate_stress"] = heat * 0.45 + hum * 0.20 + rn * 0.20 + wnd * 0.15

                peak = df.loc[df["climate_stress"].idxmax()]
                data = {
                    "source": "Open-Meteo (Exact Coordinates)",
                    "realtime": True,
                    "location": location_name,
                    "latitude": round(float(latitude), 5),
                    "longitude": round(float(longitude), 5),
                    "climate_stress": round(float(peak["climate_stress"]), 2),
                    "peak_time": peak["time"],
                    "temperature": float(peak["temperature"]),
                    "humidity": float(peak["humidity"]),
                    "rain": float(peak["rain"]),
                    "wind": float(peak["wind"]),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "hourly_series": df.to_dict(orient="records")
                }
                _WEATHER_CACHE[cache_key] = {"time": now, "data": data}
                return data

        except Exception as e:
            print("Open-Meteo Coordinate Weather API Fetch Note:", e)

        # Fallback if network API is unreachable
        return {
            "source": "Open-Meteo (Offline Fallback)",
            "realtime": False,
            "location": location_name,
            "latitude": round(float(latitude), 5),
            "longitude": round(float(longitude), 5),
            "climate_stress": 19.70,
            "peak_time": time.strftime("%Y-%m-%dT14:00"),
            "temperature": 28.5,
            "humidity": 65.0,
            "rain": 0.0,
            "wind": 12.0,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

    def get_weather_forecast(self, location="Coimbatore"):
        try:
            geo_params = {"name": location, "count": 1, "language": "en", "format": "json"}
            res_geo = requests.get(GEOCODING_API_URL, params=geo_params, timeout=4)
            geo = res_geo.json()

            if "results" in geo and len(geo["results"]) > 0:
                place = geo["results"][0]
                return self.get_weather_by_coordinates(place["latitude"], place["longitude"], place["name"])

        except Exception as e:
            print("Geocoding lookup exception:", e)

        return self.get_weather_by_coordinates(11.00555, 76.96612, location)

    def get_current_data(self, location="Coimbatore", latitude=None, longitude=None):
        if latitude is not None and longitude is not None:
            data = self.get_weather_by_coordinates(latitude, longitude, location)
        else:
            data = self.get_weather_forecast(location)

        return normalize_asset_telemetry(
            asset_id=f"WEATHER_{location.upper()}",
            asset_type="weather",
            raw_data=data,
            source_type="live_api" if data.get("realtime") else "offline_fallback",
            timestamp_str=data.get("timestamp")
        )

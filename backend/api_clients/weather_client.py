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

    def get_weather_by_coordinates(self, latitude, longitude, location_name="Custom Site", site_id="SITE-001"):
        cache_key = f"{site_id}_{round(float(latitude), 4)}_{round(float(longitude), 4)}"
        now = time.time()
        if cache_key in _WEATHER_CACHE:
            entry = _WEATHER_CACHE[cache_key]
            if now - entry["time"] < 300:  # 5-minute cache
                return entry["data"]

        try:
            w_params = {
                "latitude": float(latitude),
                "longitude": float(longitude),
                "hourly": "temperature_2m,relative_humidity_2m,precipitation,precipitation_probability,wind_speed_10m,weather_code,surface_pressure,apparent_temperature",
                "forecast_days": 7,
                "timezone": "auto"
            }
            res_w = requests.get(WEATHER_API_URL, params=w_params, timeout=5)
            weather = res_w.json()

            if "hourly" in weather and "temperature_2m" in weather["hourly"]:
                h_data = weather["hourly"]
                df_dict = {
                    "time": h_data["time"],
                    "temperature": h_data["temperature_2m"],
                    "humidity": h_data["relative_humidity_2m"],
                    "rain": h_data["precipitation"],
                    "wind": h_data["wind_speed_10m"]
                }

                if "precipitation_probability" in h_data:
                    df_dict["rain_probability"] = h_data["precipitation_probability"]
                else:
                    df_dict["rain_probability"] = [0.0] * len(h_data["time"])

                if "apparent_temperature" in h_data:
                    df_dict["apparent_temperature"] = h_data["apparent_temperature"]
                else:
                    df_dict["apparent_temperature"] = [t + 2.5 for t in h_data["temperature_2m"]]

                if "weather_code" in h_data:
                    df_dict["weather_code"] = h_data["weather_code"]
                if "surface_pressure" in h_data:
                    df_dict["surface_pressure"] = h_data["surface_pressure"]

                df = pd.DataFrame(df_dict)

                heat = np.clip((df["temperature"] - 30.0) / 15.0 * 100.0, 0.0, 100.0)
                hum = np.clip((df["humidity"] - 60.0) / 40.0 * 100.0, 0.0, 100.0)
                rn = np.clip(df["rain"] / 20.0 * 100.0, 0.0, 100.0)
                wnd = np.clip((df["wind"] - 30.0) / 40.0 * 100.0, 0.0, 100.0)
                df["climate_stress"] = heat * 0.45 + hum * 0.20 + rn * 0.20 + wnd * 0.15

                curr_row = df.iloc[0]
                peak = df.loc[df["climate_stress"].idxmax()]
                data = {
                    "site_id": site_id,
                    "source": "Open-Meteo (Exact Coordinates)",
                    "source_status": "LIVE",
                    "realtime": True,
                    "location": location_name,
                    "latitude": round(float(latitude), 5),
                    "longitude": round(float(longitude), 5),
                    "climate_stress": round(float(curr_row["climate_stress"]), 2),
                    "peak_climate_stress": round(float(peak["climate_stress"]), 2),
                    "peak_forecast_temp": round(float(df["temperature"].max()), 1),
                    "peak_time": peak["time"],
                    "temperature": float(curr_row["temperature"]),
                    "humidity": float(curr_row["humidity"]),
                    "rain": float(curr_row["rain"]),
                    "rain_probability": float(curr_row.get("rain_probability", 0.0)),
                    "apparent_temperature": float(curr_row.get("apparent_temperature", curr_row["temperature"] + 2.5)),
                    "wind": float(curr_row["wind"]),
                    "weather_code": int(curr_row.get("weather_code", 0)),
                    "surface_pressure": float(curr_row.get("surface_pressure", 1013.25)),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "hourly_series": df.to_dict(orient="records")
                }
                _WEATHER_CACHE[cache_key] = {"time": now, "data": data}
                return data

        except Exception as e:
            print("Open-Meteo Coordinate Weather API Fetch Note:", e)

        # Fallback handling: retain last valid weather result if available in cache
        if cache_key in _WEATHER_CACHE:
            entry = _WEATHER_CACHE[cache_key]
            last_data = dict(entry["data"])
            age_sec = round(now - entry["time"], 1)
            last_data["source"] = "Open-Meteo (Last Known Data)"
            last_data["source_status"] = "LAST KNOWN DATA"
            last_data["realtime"] = False
            last_data["freshness_age_seconds"] = age_sec
            return last_data

        # Fallback if network API is unreachable and no cache exists
        return {
            "site_id": site_id,
            "source": "Open-Meteo (Offline Fallback)",
            "source_status": "OFFLINE_FALLBACK",
            "message": "Forecast temporarily unavailable",
            "realtime": False,
            "location": location_name,
            "latitude": round(float(latitude), 5),
            "longitude": round(float(longitude), 5),
            "climate_stress": 19.70,
            "peak_climate_stress": 24.50,
            "peak_forecast_temp": 32.5,
            "peak_time": time.strftime("%Y-%m-%dT14:00"),
            "temperature": 28.5,
            "humidity": 65.0,
            "rain": 0.0,
            "rain_probability": 10.0,
            "apparent_temperature": 31.0,
            "wind": 12.0,
            "weather_code": 0,
            "surface_pressure": 1013.25,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

    def get_weather_forecast(self, location="Coimbatore", site_id="SITE-001"):
        try:
            geo_params = {"name": location, "count": 1, "language": "en", "format": "json"}
            res_geo = requests.get(GEOCODING_API_URL, params=geo_params, timeout=4)
            geo = res_geo.json()

            if "results" in geo and len(geo["results"]) > 0:
                place = geo["results"][0]
                return self.get_weather_by_coordinates(place["latitude"], place["longitude"], place["name"], site_id=site_id)

        except Exception as e:
            print("Geocoding lookup exception:", e)

        return self.get_weather_by_coordinates(11.00555, 76.96612, location, site_id=site_id)

    def get_current_data(self, location="Coimbatore", latitude=None, longitude=None, site_id="SITE-001"):
        if latitude is not None and longitude is not None:
            data = self.get_weather_by_coordinates(latitude, longitude, location, site_id=site_id)
        else:
            data = self.get_weather_forecast(location, site_id=site_id)

        return normalize_asset_telemetry(
            asset_id=f"WEATHER_{location.upper()}",
            asset_type="weather",
            raw_data=data,
            source_type="live_api" if data.get("realtime") else "offline_fallback",
            timestamp_str=data.get("timestamp")
        )

import requests
import pandas as pd
import numpy as np


# ============================================================
# CASCADEGUARD - CLIMATE STRESS ENGINE
# ============================================================

location = input("Enter transformer location: ")

print("\nSearching location...")


# ============================================================
# 1. GEOCODING
# ============================================================

geo_url = "https://geocoding-api.open-meteo.com/v1/search"

geo_params = {
    "name": location,
    "count": 1,
    "language": "en",
    "format": "json"
}

geo_response = requests.get(
    geo_url,
    params=geo_params
)

geo_data = geo_response.json()

if "results" not in geo_data or len(geo_data["results"]) == 0:

    print("Location not found.")
    exit()


place = geo_data["results"][0]

latitude = place["latitude"]
longitude = place["longitude"]
location_name = place["name"]

print("\nLocation:", location_name)
print("Latitude:", latitude)
print("Longitude:", longitude)


# ============================================================
# 2. WEATHER DATA
# ============================================================

weather_url = "https://api.open-meteo.com/v1/forecast"

weather_params = {

    "latitude": latitude,
    "longitude": longitude,

    "hourly":
        "temperature_2m,"
        "relative_humidity_2m,"
        "precipitation,"
        "wind_speed_10m",

    "forecast_days": 3,

    "timezone": "auto"
}


weather_response = requests.get(
    weather_url,
    params=weather_params
)

weather = weather_response.json()


# ============================================================
# 3. CREATE DATAFRAME
# ============================================================

df = pd.DataFrame({

    "time":
        weather["hourly"]["time"],

    "temperature":
        weather["hourly"]["temperature_2m"],

    "humidity":
        weather["hourly"]["relative_humidity_2m"],

    "rain":
        weather["hourly"]["precipitation"],

    "wind":
        weather["hourly"]["wind_speed_10m"]
})


print("\nWeather data received:")
print(df.head())


# ============================================================
# 4. CLIMATE STRESS COMPONENTS
# ============================================================

# Heat stress
heat_score = np.clip(
    (df["temperature"] - 30) / 15 * 100,
    0,
    100
)

# Humidity stress
humidity_score = np.clip(
    (df["humidity"] - 60) / 40 * 100,
    0,
    100
)

# Rain stress
rain_score = np.clip(
    df["rain"] / 20 * 100,
    0,
    100
)

# Wind stress
wind_score = np.clip(
    (df["wind"] - 30) / 40 * 100,
    0,
    100
)


# ============================================================
# 5. COMBINED CLIMATE STRESS
# ============================================================

df["climate_stress"] = (

    heat_score * 0.45 +

    humidity_score * 0.20 +

    rain_score * 0.20 +

    wind_score * 0.15

)


# ============================================================
# 6. MAXIMUM UPCOMING STRESS
# ============================================================

max_stress = df["climate_stress"].max()

avg_stress = df["climate_stress"].mean()

max_row = df.loc[
    df["climate_stress"].idxmax()
]


# ============================================================
# 7. CLASSIFICATION
# ============================================================

if max_stress < 30:

    level = "LOW"

elif max_stress < 60:

    level = "MODERATE"

elif max_stress < 80:

    level = "HIGH"

else:

    level = "CRITICAL"


# ============================================================
# 8. RESULT
# ============================================================

print("\n")
print("=" * 60)
print("CASCADEGUARD CLIMATE STRESS")
print("=" * 60)

print(
    f"\nLocation: {location_name}"
)

print(
    f"Maximum Climate Stress: {max_stress:.1f}/100"
)

print(
    f"Average Climate Stress: {avg_stress:.1f}/100"
)

print(
    f"Risk Level: {level}"
)

print(
    f"Peak Stress Time: {max_row['time']}"
)

print(
    f"Temperature: {max_row['temperature']:.1f} °C"
)

print(
    f"Humidity: {max_row['humidity']:.1f} %"
)

print(
    f"Rain: {max_row['rain']:.1f} mm"
)

print(
    f"Wind: {max_row['wind']:.1f} km/h"
)

print("=" * 60)
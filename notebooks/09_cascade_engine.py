import pandas as pd
import numpy as np
import joblib
import requests

from pathlib import Path


# ============================================================
# CASCADEGUARD FINAL RISK ENGINE
# ============================================================

print("=" * 70)
print("             CASCADEGUARD")
print("       CLIMATE INFRASTRUCTURE AI")
print("=" * 70)


# ============================================================
# 1. USER INPUT
# ============================================================

location = input("\nEnter transformer location: ")

print("\nEnter transformer health measurements.")

hydrogen = float(input("Hydrogen: "))
oxigen = float(input("Oxigen: "))
nitrogen = float(input("Nitrogen: "))
methane = float(input("Methane: "))
co = float(input("CO: "))
co2 = float(input("CO2: "))
ethylene = float(input("Ethylene: "))
ethane = float(input("Ethane: "))
acethylene = float(input("Acethylene: "))
dbds = float(input("DBDS: "))
power_factor = float(input("Power factor: "))
interfacial_v = float(input("Interfacial V: "))
dielectric = float(input("Dielectric rigidity: "))
water = float(input("Water content: "))


# ============================================================
# 2. LOAD HEALTH MODEL
# ============================================================

health_model = joblib.load(
    "models/health_index_xgboost.pkl"
)

health_features = [
    "Hydrogen",
    "Oxigen",
    "Nitrogen",
    "Methane",
    "CO",
    "CO2",
    "Ethylene",
    "Ethane",
    "Acethylene",
    "DBDS",
    "Power factor",
    "Interfacial V",
    "Dielectric rigidity",
    "Water content"
]

health_input = pd.DataFrame([[
    hydrogen,
    oxigen,
    nitrogen,
    methane,
    co,
    co2,
    ethylene,
    ethane,
    acethylene,
    dbds,
    power_factor,
    interfacial_v,
    dielectric,
    water
]], columns=health_features)


health_index = float(
    health_model.predict(
        health_input
    )[0]
)

health_index = np.clip(
    health_index,
    0,
    100
)


health_risk = 100 - health_index


# ============================================================
# 3. CLIMATE DATA
# ============================================================

print("\nSearching climate data...")

geo_url = (
    "https://geocoding-api.open-meteo.com/v1/search"
)

geo_params = {
    "name": location,
    "count": 1,
    "language": "en",
    "format": "json"
}

geo_response = requests.get(
    geo_url,
    params=geo_params,
    timeout=20
)

geo_data = geo_response.json()

if (
    "results" not in geo_data
    or len(geo_data["results"]) == 0
):

    print("Location not found.")
    exit()


place = geo_data["results"][0]

latitude = place["latitude"]
longitude = place["longitude"]

location_name = place["name"]


# ============================================================
# 4. WEATHER
# ============================================================

weather_url = (
    "https://api.open-meteo.com/v1/forecast"
)

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
    params=weather_params,
    timeout=20
)

weather = weather_response.json()


weather_df = pd.DataFrame({

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


# ============================================================
# 5. CLIMATE STRESS
# ============================================================

heat_score = np.clip(
    (weather_df["temperature"] - 30)
    / 15 * 100,
    0,
    100
)

humidity_score = np.clip(
    (weather_df["humidity"] - 60)
    / 40 * 100,
    0,
    100
)

rain_score = np.clip(
    weather_df["rain"] / 20 * 100,
    0,
    100
)

wind_score = np.clip(
    (weather_df["wind"] - 30)
    / 40 * 100,
    0,
    100
)


weather_df["climate_stress"] = (

    heat_score * 0.45 +

    humidity_score * 0.20 +

    rain_score * 0.20 +

    wind_score * 0.15
)


climate_stress = float(
    weather_df["climate_stress"].max()
)


peak = weather_df.loc[
    weather_df["climate_stress"].idxmax()
]


# ============================================================
# 6. OPERATIONAL RISK
# ============================================================

# For now, because the monitoring dataset does not correspond
# directly to the DGA health-index inputs, we use the latest
# operational record from the monitoring dataset.

operational_model = joblib.load(
    "models/operational_stress_xgboost_v2.pkl"
)

monitoring = pd.read_csv(
    "data/processed/transformer_merged.csv"
)

monitoring["DeviceTimeStamp"] = pd.to_datetime(
    monitoring["DeviceTimeStamp"]
)

monitoring = monitoring.sort_values(
    "DeviceTimeStamp"
)

latest = monitoring.iloc[-1]


operational_features = [
    "ATI",
    "OTI",
    "WTI",
    "OLI",
    "VL1",
    "VL2",
    "VL3",
    "VL12",
    "VL23",
    "VL31",
    "IL1",
    "IL2",
    "IL3",
    "INUT",
    "WL1",
    "WL2",
    "WL3",
    "VAL1",
    "VAL2",
    "VAL3",
    "RVAL1",
    "RVAL2",
    "RVAL3",
    "PFL1",
    "PFL2",
    "PFL3",
    "Avg_PF",
    "Sum_PF",
    "FRQ",
    "THDVL1",
    "THDVL2",
    "THDVL3",
    "THDIL1",
    "THDIL2",
    "THDIL3",
    "KW",
    "KVA",
    "KVAR",
    "MPD",
    "MKVAD"
]


operational_input = (
    latest[operational_features]
    .astype(float)
    .fillna(0)
    .to_frame()
    .T
)


operational_probability = float(
    operational_model.predict_proba(
        operational_input
    )[0][1]
)

operational_risk = (
    operational_probability * 100
)


# ============================================================
# 7. FINAL CASCADE RISK
# ============================================================

final_risk = (

    health_risk * 0.40 +

    operational_risk * 0.40 +

    climate_stress * 0.20
)


final_risk = np.clip(
    final_risk,
    0,
    100
)


# ============================================================
# 8. RISK LEVEL
# ============================================================

if final_risk < 25:

    risk_level = "LOW"

elif final_risk < 50:

    risk_level = "MODERATE"

elif final_risk < 75:

    risk_level = "HIGH"

else:

    risk_level = "CRITICAL"


# ============================================================
# 9. RECOMMENDATION
# ============================================================

if risk_level == "LOW":

    recommendation = (
        "Continue normal monitoring."
    )

elif risk_level == "MODERATE":

    recommendation = (
        "Increase monitoring frequency "
        "and inspect risk indicators."
    )

elif risk_level == "HIGH":

    recommendation = (
        "Prioritize transformer inspection "
        "and evaluate load/cooling conditions."
    )

else:

    recommendation = (
        "Immediate engineering assessment "
        "and protective action recommended."
    )


# ============================================================
# 10. DISPLAY RESULT
# ============================================================

print("\n")
print("=" * 70)
print("             CASCADEGUARD RESULT")
print("=" * 70)

print(
    f"\nLocation: {location_name}"
)

print(
    f"Coordinates: "
    f"{latitude:.4f}, {longitude:.4f}"
)


print("\n----------------------------------------")
print("RISK COMPONENTS")
print("----------------------------------------")

print(
    f"Health Index:       {health_index:.1f}/100"
)

print(
    f"Health Risk:        {health_risk:.1f}/100"
)

print(
    f"Operational Risk:   {operational_risk:.1f}/100"
)

print(
    f"Climate Stress:     {climate_stress:.1f}/100"
)


print("\n----------------------------------------")
print("FINAL CASCADE RISK")
print("----------------------------------------")

print(
    f"\n        {final_risk:.1f}/100"
)

print(
    f"        {risk_level}"
)


print("\n----------------------------------------")
print("CLIMATE FORECAST")
print("----------------------------------------")

print(
    f"Peak time: {peak['time']}"
)

print(
    f"Temperature: {peak['temperature']:.1f} °C"
)

print(
    f"Humidity: {peak['humidity']:.1f} %"
)

print(
    f"Rain: {peak['rain']:.1f} mm"
)

print(
    f"Wind: {peak['wind']:.1f} km/h"
)


print("\n----------------------------------------")
print("RECOMMENDED ACTION")
print("----------------------------------------")

print(
    recommendation
)

print("\n" + "=" * 70)
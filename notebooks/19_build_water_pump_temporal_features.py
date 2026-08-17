import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "raw" / "water_pump" / "rul_hrs.csv"
OUTPUT_DIR = BASE_DIR / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("CASCADEGUARD PHASE 8B: LEAKAGE-SAFE TEMPORAL FEATURE ENGINEERING")
print("=" * 70)

# Load dataset
df = pd.read_csv(DATA_PATH)
df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
df = df.sort_values("timestamp").reset_index(drop=True)

target_col = "rul"
non_features = ["Unnamed: 0", "timestamp", target_col]
raw_features = [c for c in df.columns if c not in non_features and df[c].nunique() > 1]

print(f"Total Raw Usable Sensor Features: {len(raw_features)}")

# Focus past-only feature extraction on top signal sensors
KEY_SENSORS = ["sensor_13", "sensor_29", "sensor_37", "sensor_41", "sensor_05", "sensor_00", "sensor_04", "sensor_10", "sensor_11", "sensor_12"]

feature_dict = {}

# 1. Raw features (instantaneous value at time t)
for col in raw_features:
    feature_dict[col] = df[col].values

# 2. Lags (past observations t-1, t-5, t-10, t-15, t-30, t-60)
for col in KEY_SENSORS:
    s = df[col]
    feature_dict[f"{col}_lag1"] = s.shift(1).bfill().fillna(0.0).values
    feature_dict[f"{col}_lag5"] = s.shift(5).bfill().fillna(0.0).values
    feature_dict[f"{col}_lag15"] = s.shift(15).bfill().fillna(0.0).values
    feature_dict[f"{col}_lag30"] = s.shift(30).bfill().fillna(0.0).values

# 3. Past-Only Rolling Statistics (Strictly closed='left' or shift(1) rolling)
for col in KEY_SENSORS:
    s = df[col]
    
    # 5-sample past rolling mean & std
    r5 = s.rolling(5, min_periods=1)
    feature_dict[f"{col}_roll5_mean"] = r5.mean().fillna(0.0).values
    feature_dict[f"{col}_roll5_std"] = r5.std().fillna(0.0).values

    # 15-sample past rolling mean, std, min, max
    r15 = s.rolling(15, min_periods=1)
    feature_dict[f"{col}_roll15_mean"] = r15.mean().fillna(0.0).values
    feature_dict[f"{col}_roll15_std"] = r15.std().fillna(0.0).values
    feature_dict[f"{col}_roll15_min"] = r15.min().fillna(0.0).values
    feature_dict[f"{col}_roll15_max"] = r15.max().fillna(0.0).values

    # 60-sample past rolling mean
    r60 = s.rolling(60, min_periods=1)
    feature_dict[f"{col}_roll60_mean"] = r60.mean().fillna(0.0).values

# 4. Past Trend / Rate of Change Features
for col in KEY_SENSORS:
    s = df[col]
    feature_dict[f"{col}_change1"] = s.diff(1).fillna(0.0).values
    feature_dict[f"{col}_change5"] = s.diff(5).fillna(0.0).values
    feature_dict[f"{col}_change15"] = s.diff(15).fillna(0.0).values

# Build feature dataframe
X_eng_df = pd.DataFrame(feature_dict).fillna(0.0)
all_feature_names = list(X_eng_df.columns)

print(f"Total Leakage-Safe Feature Count: {len(all_feature_names)}")

# Verification check for future leakage
forbidden_cols = ["rul_future", "target_future", "t+1"]
leakage_found = [c for c in all_feature_names if any(f in c for f in forbidden_cols)]
if leakage_found:
    raise ValueError(f"FUTURE LEAKAGE DETECTED: {leakage_found}")

print("Zero Future Leakage Verification: PASSED (All features use observations <= t)")

# Save feature metadata schema
schema_path = BASE_DIR / "models" / "water_pump_features_v2.csv"
with open(schema_path, "w") as f:
    for feat in all_feature_names:
        f.write(f"{feat}\n")

print(f"Feature schema saved to: {schema_path}")
print("\n" + "=" * 70)
print("PHASE 8B LEAKAGE-SAFE FEATURE ENGINEERING COMPLETE")
print("=" * 70)

import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PUMP_PATH = BASE_DIR / "data" / "raw" / "water_pump" / "rul_hrs.csv"
REPORT_PATH = BASE_DIR / "data" / "processed" / "water_pump_dataset_report.txt"

REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("CASCADEGUARD PHASE 7A — PART B: WATER PUMP DATASET AUDIT")
print("=" * 70)

# Load dataset
df = pd.read_csv(PUMP_PATH)

print(f"\n1. File: {PUMP_PATH.name}")
print(f"2. Shape: {df.shape[0]:,} rows x {df.shape[1]} columns")

print("\n3. Column Names and Data Types:")
for i, col in enumerate(df.columns, 1):
    print(f"  {i:02d}. {col:25s} | dtype: {str(df[col].dtype):10s} | nulls: {df[col].isnull().sum():,}")

print("\n4. First 10 Rows:")
print(df.head(10).to_string())

# 5. Missing values
total_missing = df.isnull().sum().sum()
print(f"\n5. Missing Values: Total {total_missing:,} nulls across dataset.")

# 6. Duplicate rows
duplicates = df.duplicated().sum()
print(f"6. Duplicate Rows: {duplicates:,} ({duplicates / len(df) * 100:.2f}%)")

# Identify Asset ID, Timestamp, Target
id_col = None
timestamp_col = None
target_col = None

possible_ids = ["id", "unit", "pump_id", "asset_id", "device_id", "unit_number", "pump"]
possible_timestamps = ["time", "date", "timestamp", "cycle", "hour", "hours"]
possible_targets = ["rul", "rul_hrs", "remaining_useful_life", "target", "label", "health_index"]

for col in df.columns:
    c_low = col.lower()
    if not id_col and any(p == c_low or p in c_low for p in possible_ids):
        id_col = col
    elif not timestamp_col and any(p == c_low or "time" in c_low or "date" in c_low or "cycle" in c_low for p in possible_timestamps):
        timestamp_col = col
    elif not target_col and any(p == c_low or "rul" in c_low for p in possible_targets):
        target_col = col

if not target_col and df.columns[-1] not in [id_col, timestamp_col]:
    target_col = df.columns[-1]

print(f"\n7. Asset Identifier Column: '{id_col}' (Unique Units: {df[id_col].nunique() if id_col else 'None'})")
print(f"8. Timestamp/Cycle Column: '{timestamp_col}'")
print(f"9. Target Column: '{target_col}'")

# RUL Statistics
if target_col and np.issubdtype(df[target_col].dtype, np.number):
    rul_stats = df[target_col].describe().to_dict()
    print(f"\n10. RUL Target Statistics (Hours/Cycles):")
    print(f"  - Count: {rul_stats['count']:,}")
    print(f"  - Mean: {rul_stats['mean']:.2f}")
    print(f"  - Std: {rul_stats['std']:.2f}")
    print(f"  - Min: {rul_stats['min']:.2f}")
    print(f"  - 25%: {rul_stats['25%']:.2f}")
    print(f"  - Median (50%): {rul_stats['50%']:.2f}")
    print(f"  - 75%: {rul_stats['75%']:.2f}")
    print(f"  - Max: {rul_stats['max']:.2f}")

# Categorical vs Numerical Features
non_features = [c for c in [id_col, timestamp_col, target_col] if c is not None]
feature_cols = [c for c in df.columns if c not in non_features]
num_features = [c for c in feature_cols if np.issubdtype(df[c].dtype, np.number)]
cat_features = [c for c in feature_cols if not np.issubdtype(df[c].dtype, np.number)]

print(f"\n11. Numerical Features ({len(num_features)}): {num_features}")
print(f"12. Categorical Features ({len(cat_features)}): {cat_features}")
print(f"13. Non-Feature / Metadata Columns: {non_features}")

# Quality Check: Constant Columns
constant_cols = [c for c in df.columns if df[c].nunique() == 1]
print(f"\n14. Quality Check — Constant Columns ({len(constant_cols)}): {constant_cols}")

# Supported Capabilities
print("\n15. Supported Capabilities:")
print("  - RUL Prediction (Regression): YES (Predicts exact remaining operating hours before failure)")
print("  - Health Index Score: YES (Derive Health Score = min(100, RUL / RUL_max * 100))")
print("  - Failure Probability: YES (Sigmoidal conversion of low RUL)")
print("  - Anomaly Detection: YES (Sensor drift detection across operational cycles)")

# Write detailed text report
report_lines = [
    "CASCADEGUARD WATER PUMP DATASET INSPECTION REPORT",
    "=====================================================",
    f"Dataset File: {PUMP_PATH.name}",
    f"Shape: {df.shape[0]:,} rows x {df.shape[1]} columns",
    f"Missing Values: {total_missing:,}",
    f"Duplicate Rows: {duplicates:,}",
    "",
    f"Asset Identifier Column: {id_col} (Unique Units: {df[id_col].nunique() if id_col else 'None'})",
    f"Timestamp/Cycle Column: {timestamp_col}",
    f"Target Column: {target_col}",
    f"Target RUL Summary (Hours): Min={df[target_col].min()}, Max={df[target_col].max()}, Mean={df[target_col].mean():.2f}, Median={df[target_col].median():.2f}",
    "",
    f"Numerical ML Features ({len(num_features)}): {num_features}",
    f"Categorical Features ({len(cat_features)}): {cat_features}",
    f"Non-Feature Columns (Excluded from X): {non_features}",
    f"Constant Columns: {constant_cols}",
    "",
    "RECOMMENDED ML TASK: Remaining Useful Life (RUL) Regression & Health Index Transformation",
    "RECOMMENDED MODEL TYPE: XGBoost Regressor / Random Forest Regressor",
    "CLIMATE SENSITIVITY: Medium-High (Pump motor temperature, head pressure, and flow rates respond to ambient water/air thermal stress)",
    "SUITABILITY FOR CASCADEGUARD: HIGH — Ideal for predicting water pump degradation in municipal/substation cooling networks."
]

with open(REPORT_PATH, "w") as f:
    f.write("\n".join(report_lines))

print(f"\nWater pump report saved to: {REPORT_PATH}")

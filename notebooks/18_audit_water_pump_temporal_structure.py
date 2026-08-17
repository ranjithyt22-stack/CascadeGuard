import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "raw" / "water_pump" / "rul_hrs.csv"
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("CASCADEGUARD PHASE 8A: WATER PUMP TEMPORAL & LEAKAGE AUDIT")
print("=" * 70)

# 1. Load Dataset & Audit Timestamps
df = pd.read_csv(DATA_PATH)
n_obs = len(df)
print(f"Total Observations: {n_obs:,}")

time_col = "timestamp" if "timestamp" in df.columns else None
if time_col:
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.sort_values("timestamp").reset_index(drop=True)
    t_min = df["timestamp"].min()
    t_max = df["timestamp"].max()
    n_unique_time = df["timestamp"].nunique()
    dup_time = df["timestamp"].duplicated().sum()

    time_diffs = df["timestamp"].diff()
    med_interval = time_diffs.median()
    max_gap = time_diffs.max()
    mode_interval = time_diffs.mode()[0] if len(time_diffs.mode()) > 0 else med_interval

    print(f"Start Timestamp: {t_min}")
    print(f"End Timestamp:   {t_max}")
    print(f"Unique Timestamps: {n_unique_time:,}")
    print(f"Duplicated Timestamps: {dup_time:,}")
    print(f"Median Sampling Interval: {med_interval}")
    print(f"Most Common Sampling Interval: {mode_interval}")
    print(f"Largest Time Gap: {max_gap}")

# 2. Temporal Distribution (Monthly & Hourly Breakdown)
if time_col:
    df["month"] = df["timestamp"].dt.strftime("%Y-%m")
    month_counts = df["month"].value_counts().sort_index().to_dict()
    print(f"\nObservations by Month: {month_counts}")

# 3. Target RUL Analysis
target_col = "rul"
rul = df[target_col]
p10, p25, p50, p75, p90 = np.percentile(rul, [10, 25, 50, 75, 90])

print(f"\nTarget RUL Summary Statistics (Hours):")
print(f"  Count:  {len(rul):,}")
print(f"  Mean:   {rul.mean():.2f}")
print(f"  Median: {p50:.2f}")
print(f"  Std:    {rul.std():.2f}")
print(f"  Min:    {rul.min():.2f}")
print(f"  Max:    {rul.max():.2f}")
print(f"  P10: {p10:.2f} | P25: {p25:.2f} | P50: {p50:.2f} | P75: {p75:.2f} | P90: {p90:.2f}")

# Plot Target Over Time
plt.figure(figsize=(12, 5))
plt.plot(df["timestamp"], df["rul"], color="#8f34eb", linewidth=1.0)
plt.title("Water Pump RUL Degradation Trajectory Over Time (April–July 2018)")
plt.xlabel("Timestamp")
plt.ylabel("RUL (Hours)")
plt.grid(True, linestyle="--", alpha=0.5)
plt.tight_layout()
plt.savefig(REPORTS_DIR / "water_pump_target_over_time.png", dpi=150)
plt.close()
print(f"Target trajectory plot saved to: {REPORTS_DIR / 'water_pump_target_over_time.png'}")

# 4. Autocorrelation Leakage Audit
print("\n" + "=" * 50)
print("AUTOCORRELATION LEAKAGE AUDIT")
print("=" * 50)

lags = [1, 5, 10, 15, 30, 60, 120]
key_variables = ["rul", "sensor_00", "sensor_04", "sensor_10", "sensor_13"]

lag_report_rows = []
for var in key_variables:
    if var in df.columns:
        s = df[var]
        for lag in lags:
            corr = s.autocorr(lag=lag)
            lag_report_rows.append({"Variable": var, "Lag": f"lag_{lag} ({lag}m)", "Autocorrelation": round(corr, 4)})

lag_df = pd.DataFrame(lag_report_rows)
print(lag_df.to_string(index=False))

# 5. Operating-Cycle / Asset Audit
candidate_id_cols = [c for c in df.columns if any(p in c.lower() for p in ["unit", "pump_id", "asset", "cycle", "run_id", "status"])]
print(f"\nOperating-Cycle / Asset Identifier Columns Found: {candidate_id_cols}")

print("\n" + "=" * 70)
print("PHASE 8A TEMPORAL & LEAKAGE AUDIT COMPLETE")
print("=" * 70)

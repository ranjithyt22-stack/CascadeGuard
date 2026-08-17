import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
import matplotlib.pyplot as plt

from sklearn.ensemble import HistGradientBoostingRegressor
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, median_absolute_error

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "raw" / "water_pump" / "rul_hrs.csv"
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("CASCADEGUARD PHASE 7C: WATER PUMP DEEP ANALYSIS & MODEL IMPROVEMENT")
print("=" * 70)

# 1. LOAD DATASET & DEEP ANALYSIS
df = pd.read_csv(DATA_PATH)
print(f"Dataset Shape: {df.shape[0]:,} rows x {df.shape[1]} columns")

has_time = "timestamp" in df.columns
if has_time:
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.sort_values("timestamp").reset_index(drop=True)
    t_min, t_max = df["timestamp"].min(), df["timestamp"].max()
    t_diff = df["timestamp"].diff().median()
    print(f"Timestamp Range: {t_min} to {t_max}")
    print(f"Sampling Frequency (Median Interval): {t_diff}")

dup_rows = df.duplicated().sum()
dup_time = df["timestamp"].duplicated().sum() if has_time else 0
print(f"Duplicate Rows: {dup_rows:,} | Duplicate Timestamps: {dup_time:,}")

machine_id_cols = [c for c in df.columns if any(p in c.lower() for p in ["unit", "machine", "device", "pump_id", "asset"])]
print(f"Machine / Unit ID Columns Found: {machine_id_cols}")

target_col = "rul"
non_features = ["Unnamed: 0", "timestamp", target_col] + machine_id_cols
raw_features = [c for c in df.columns if c not in non_features]

constant_features = [c for c in raw_features if df[c].nunique() <= 1]
print(f"Constant Sensors ({len(constant_features)}): {constant_features}")

usable_raw_features = [c for c in raw_features if c not in constant_features]
print(f"Usable Raw Features ({len(usable_raw_features)}): {len(usable_raw_features)}")

rul = df[target_col]
print(f"\nRUL Statistics (Hours):")
print(f"  Count: {len(rul):,} | Min: {rul.min():.2f} | Max: {rul.max():.2f} | Mean: {rul.mean():.2f} | Median: {rul.median():.2f} | Std: {rul.std():.2f}")

# Sensor Correlations with RUL
corrs = df[usable_raw_features].apply(lambda x: x.corr(rul))
abs_corrs = corrs.abs().sort_values(ascending=False)
top_20_features = abs_corrs.head(20).index.tolist()

print("\nTop 20 Raw Features by Pearson Correlation with RUL:")
for f in top_20_features:
    print(f"  - {f:15s} | Corr: {corrs[f]:+.4f} | Abs Corr: {abs_corrs[f]:.4f}")

# Correlations by RUL Bucket
print("\nFeature Correlations across RUL Buckets:")
b_gt_500 = df[df[target_col] > 500]
b_250_500 = df[(df[target_col] >= 250) & (df[target_col] <= 500)]
b_100_250 = df[(df[target_col] >= 100) & (df[target_col] < 250)]
b_lt_100 = df[df[target_col] < 100]

top_5_f = top_20_features[:5]
print(f"{'Feature':12s} | {'RUL>500':10s} | {'250-500':10s} | {'100-250':10s} | {'RUL<100':10s}")
print("-" * 60)
for f in top_5_f:
    c1 = b_gt_500[f].corr(b_gt_500[target_col]) if len(b_gt_500) > 0 else 0
    c2 = b_250_500[f].corr(b_250_500[target_col]) if len(b_250_500) > 0 else 0
    c3 = b_100_250[f].corr(b_100_250[target_col]) if len(b_100_250) > 0 else 0
    c4 = b_lt_100[f].corr(b_lt_100[target_col]) if len(b_lt_100) > 0 else 0
    print(f"{f:12s} | {c1:+10.4f} | {c2:+10.4f} | {c3:+10.4f} | {c4:+10.4f}")

# 2. FEATURE ENGINEERING (Past-Only Rolling Statistics)
print("\n[STEP 2] Feature Engineering (Past-Only Rolling Stats)...")
KEY_SENSORS = top_20_features[:10]
eng_df = df[usable_raw_features].copy()

for col in KEY_SENSORS:
    s = df[col]
    eng_df[f"{col}_roll15_mean"] = s.rolling(15, min_periods=1).mean().fillna(0.0)
    eng_df[f"{col}_roll30_mean"] = s.rolling(30, min_periods=1).mean().fillna(0.0)
    eng_df[f"{col}_diff1"] = s.diff(1).fillna(0.0)

all_feature_names = list(eng_df.columns)
print(f"Total Engineered Feature Count: {len(all_feature_names)}")

X_eng = eng_df.values
y = df[target_col].values

# 3. BASELINE MODELS
print("\n[STEP 3] Evaluating Baseline Predictions...")
n_samples = len(df)
n_train = int(n_samples * 0.80)

y_train_chrono, y_test_chrono = y[:n_train], y[n_train:]
X_train_chrono, X_test_chrono = X_eng[:n_train], X_eng[n_train:]

# Baseline A: Predict Mean of Train
mean_pred = np.full(len(y_test_chrono), y_train_chrono.mean())
base_a_mae = mean_absolute_error(y_test_chrono, mean_pred)
base_a_rmse = np.sqrt(mean_squared_error(y_test_chrono, mean_pred))
base_a_r2 = r2_score(y_test_chrono, mean_pred)

# Baseline B: Predict Median of Train
median_pred = np.full(len(y_test_chrono), np.median(y_train_chrono))
base_b_mae = mean_absolute_error(y_test_chrono, median_pred)
base_b_rmse = np.sqrt(mean_squared_error(y_test_chrono, median_pred))
base_b_r2 = r2_score(y_test_chrono, median_pred)

print(f"Baseline A (Train Mean):   MAE = {base_a_mae:.2f} hrs | RMSE = {base_a_rmse:.2f} hrs | R² = {base_a_r2:.4f}")
print(f"Baseline B (Train Median): MAE = {base_b_mae:.2f} hrs | RMSE = {base_b_rmse:.2f} hrs | R² = {base_b_r2:.4f}")

# 4. VALIDATION STRATEGY COMPARISON (Random vs Chronological)
print("\n[STEP 4] Validation Strategy Comparison (XGBoost Regressor)...")

# A. Random Split (80/20)
X_train_rnd, X_test_rnd, y_train_rnd, y_test_rnd = train_test_split(
    X_eng, y, test_size=0.20, random_state=42
)
model_xgb_rnd = XGBClassifier() if False else XGBRegressor(objective="reg:squarederror", n_estimators=60, max_depth=5, learning_rate=0.05, random_state=42, n_jobs=-1)
model_xgb_rnd.fit(X_train_rnd, y_train_rnd)
pred_xgb_rnd = model_xgb_rnd.predict(X_test_rnd)

xgb_rnd_mae = mean_absolute_error(y_test_rnd, pred_xgb_rnd)
xgb_rnd_rmse = np.sqrt(mean_squared_error(y_test_rnd, pred_xgb_rnd))
xgb_rnd_r2 = r2_score(y_test_rnd, pred_xgb_rnd)

# B. Chronological Split (80/20)
model_xgb_chrono = XGBRegressor(objective="reg:squarederror", n_estimators=60, max_depth=5, learning_rate=0.05, random_state=42, n_jobs=-1)
model_xgb_chrono.fit(X_train_chrono, y_train_chrono)
pred_xgb_chrono = model_xgb_chrono.predict(X_test_chrono)

xgb_chrono_mae = mean_absolute_error(y_test_chrono, pred_xgb_chrono)
xgb_chrono_rmse = np.sqrt(mean_squared_error(y_test_chrono, pred_xgb_chrono))
xgb_chrono_r2 = r2_score(y_test_chrono, pred_xgb_chrono)

print(f"XGBoost [RANDOM SPLIT]:        MAE = {xgb_rnd_mae:.2f} hrs | RMSE = {xgb_rnd_rmse:.2f} hrs | R² = {xgb_rnd_r2:.4f}")
print(f"XGBoost [CHRONOLOGICAL SPLIT]: MAE = {xgb_chrono_mae:.2f} hrs | RMSE = {xgb_chrono_rmse:.2f} hrs | R² = {xgb_chrono_r2:.4f}")

# 5. MODEL COMPARISON ON CHRONOLOGICAL SPLIT
print("\n[STEP 5] Comparing Regression Models on Chronological Split...")

# HistGradientBoosting Regressor
model_hgb = HistGradientBoostingRegressor(max_iter=80, max_depth=5, random_state=42)
model_hgb.fit(X_train_chrono, y_train_chrono)
pred_hgb = model_hgb.predict(X_test_chrono)
hgb_mae = mean_absolute_error(y_test_chrono, pred_hgb)
hgb_rmse = np.sqrt(mean_squared_error(y_test_chrono, pred_hgb))
hgb_r2 = r2_score(y_test_chrono, pred_hgb)

print(f"  - XGBoost:          MAE = {xgb_chrono_mae:.2f} hrs | RMSE = {xgb_chrono_rmse:.2f} hrs | R² = {xgb_chrono_r2:.4f}")
print(f"  - HistGradBoosting: MAE = {hgb_mae:.2f} hrs | RMSE = {hgb_rmse:.2f} hrs | R² = {hgb_r2:.4f}")

# Feature Analysis Export
feature_analysis_df = pd.DataFrame({
    "feature": usable_raw_features,
    "pearson_corr": [corrs[f] for f in usable_raw_features],
    "abs_pearson_corr": [abs_corrs[f] for f in usable_raw_features]
}).sort_values("abs_pearson_corr", ascending=False).reset_index(drop=True)

feature_analysis_path = MODELS_DIR / "water_pump_feature_analysis.csv"
feature_analysis_df.to_csv(feature_analysis_path, index=False)
print(f"\nFeature analysis saved to: {feature_analysis_path}")

print("\n" + "=" * 65)
print("PHASE 7C MODEL IMPROVEMENT SCRIPT COMPLETE")
print("=" * 65)

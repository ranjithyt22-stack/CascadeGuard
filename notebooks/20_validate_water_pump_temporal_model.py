import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path

from sklearn.ensemble import HistGradientBoostingRegressor
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, median_absolute_error

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "raw" / "water_pump" / "rul_hrs.csv"
MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("CASCADEGUARD PHASE 8C: WALK-FORWARD TEMPORAL VALIDATION")
print("=" * 70)

# Load dataset
df = pd.read_csv(DATA_PATH)
df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
df = df.sort_values("timestamp").reset_index(drop=True)

target_col = "rul"
non_features = ["Unnamed: 0", "timestamp", target_col]
raw_features = [c for c in df.columns if c not in non_features and df[c].nunique() > 1]
KEY_SENSORS = ["sensor_13", "sensor_29", "sensor_37", "sensor_41", "sensor_05", "sensor_00", "sensor_04", "sensor_10", "sensor_11", "sensor_12"]

# Construct Leakage-Safe Past-Only Features
feature_dict = {col: df[col].values for col in raw_features}
for col in KEY_SENSORS:
    s = df[col]
    feature_dict[f"{col}_lag1"] = s.shift(1).bfill().fillna(0.0).values
    feature_dict[f"{col}_lag5"] = s.shift(5).bfill().fillna(0.0).values
    feature_dict[f"{col}_lag15"] = s.shift(15).bfill().fillna(0.0).values

    r15 = s.rolling(15, min_periods=1)
    feature_dict[f"{col}_roll15_mean"] = r15.mean().fillna(0.0).values
    feature_dict[f"{col}_roll15_std"] = r15.std().fillna(0.0).values
    feature_dict[f"{col}_diff1"] = s.diff(1).fillna(0.0).values

X_eng_df = pd.DataFrame(feature_dict).fillna(0.0)
X = X_eng_df.values
y = df[target_col].values
timestamps = df["timestamp"].values

n_total = len(df)
step_size = int(n_total * 0.20)

# Define 3 Temporal Expanding Folds
# Fold 1: Train 40% (0 to 2*step), Test (2*step to 3*step)
# Fold 2: Train 60% (0 to 3*step), Test (3*step to 4*step)
# Fold 3: Train 80% (0 to 4*step), Test (4*step to end)
folds = [
    {"fold": 1, "train_end": 2 * step_size, "test_end": 3 * step_size},
    {"fold": 2, "train_end": 3 * step_size, "test_end": 4 * step_size},
    {"fold": 3, "train_end": 4 * step_size, "test_end": n_total}
]

walk_forward_results = []

for f_info in folds:
    fold_num = f_info["fold"]
    t_end = f_info["train_end"]
    val_end = f_info["test_end"]

    X_train, y_train = X[:t_end], y[:t_end]
    X_test, y_test = X[t_end:val_end], y[t_end:val_end]

    t_train_start = timestamps[0]
    t_train_end = timestamps[t_end - 1]
    t_test_start = timestamps[t_end]
    t_test_end = timestamps[val_end - 1]

    print(f"\n" + "=" * 50)
    print(f"FOLD {fold_num} WALK-FORWARD EVALUATION")
    print(f"Train Period: {t_train_start} to {t_train_end} ({len(y_train):,} samples)")
    print(f"Test Period:  {t_test_start} to {t_test_end} ({len(y_test):,} samples)")

    # 1. Baseline 1: Train Median
    median_pred = np.full(len(y_test), np.median(y_train))
    med_mae = mean_absolute_error(y_test, median_pred)
    med_rmse = np.sqrt(mean_squared_error(y_test, median_pred))
    med_r2 = r2_score(y_test, median_pred)

    # 2. Baseline 2: Train Mean
    mean_pred = np.full(len(y_test), y_train.mean())
    mean_mae = mean_absolute_error(y_test, mean_pred)
    mean_rmse = np.sqrt(mean_squared_error(y_test, mean_pred))
    mean_r2 = r2_score(y_test, mean_pred)

    # 3. Model 1: HistGradientBoostingRegressor
    model_hgb = HistGradientBoostingRegressor(max_iter=80, max_depth=5, random_state=42)
    model_hgb.fit(X_train, y_train)
    pred_hgb = model_hgb.predict(X_test)
    hgb_mae = mean_absolute_error(y_test, pred_hgb)
    hgb_rmse = np.sqrt(mean_squared_error(y_test, pred_hgb))
    hgb_r2 = r2_score(y_test, pred_hgb)
    hgb_p90 = np.percentile(np.abs(y_test - pred_hgb), 90)

    # 4. Model 2: XGBoost Regressor
    model_xgb = XGBRegressor(n_estimators=60, max_depth=5, learning_rate=0.05, random_state=42, n_jobs=-1)
    model_xgb.fit(X_train, y_train)
    pred_xgb = model_xgb.predict(X_test)
    xgb_mae = mean_absolute_error(y_test, pred_xgb)
    xgb_rmse = np.sqrt(mean_squared_error(y_test, pred_xgb))
    xgb_r2 = r2_score(y_test, pred_xgb)
    xgb_p90 = np.percentile(np.abs(y_test - pred_xgb), 90)

    print(f"  Baseline (Train Median): MAE = {med_mae:.2f}h | RMSE = {med_rmse:.2f}h | R² = {med_r2:.4f}")
    print(f"  Baseline (Train Mean):   MAE = {mean_mae:.2f}h | RMSE = {mean_rmse:.2f}h | R² = {mean_r2:.4f}")
    print(f"  HistGradientBoosting:   MAE = {hgb_mae:.2f}h | RMSE = {hgb_rmse:.2f}h | R² = {hgb_r2:.4f} | P90_AE = {hgb_p90:.2f}h")
    print(f"  XGBoost Regressor:       MAE = {xgb_mae:.2f}h | RMSE = {xgb_rmse:.2f}h | R² = {xgb_r2:.4f} | P90_AE = {xgb_p90:.2f}h")

    walk_forward_results.append({
        "fold": fold_num,
        "test_period": f"{t_test_start} to {t_test_end}",
        "baseline_median": {"mae": med_mae, "rmse": med_rmse, "r2": med_r2},
        "baseline_mean": {"mae": mean_mae, "rmse": mean_rmse, "r2": mean_r2},
        "hist_grad_boosting": {"mae": hgb_mae, "rmse": hgb_rmse, "r2": hgb_r2, "p90_ae": hgb_p90},
        "xgboost": {"mae": xgb_mae, "rmse": xgb_rmse, "r2": xgb_r2, "p90_ae": xgb_p90}
    })

# Summary across all folds
avg_hgb_mae = np.mean([f["hist_grad_boosting"]["mae"] for f in walk_forward_results])
avg_hgb_r2 = np.mean([f["hist_grad_boosting"]["r2"] for f in walk_forward_results])
avg_xgb_mae = np.mean([f["xgboost"]["mae"] for f in walk_forward_results])
avg_xgb_r2 = np.mean([f["xgboost"]["r2"] for f in walk_forward_results])
avg_med_mae = np.mean([f["baseline_median"]["mae"] for f in walk_forward_results])

print("\n" + "=" * 65)
print("WALK-FORWARD VALIDATION SUMMARY ACROSS ALL FOLDS:")
print(f"  Baseline Median Average MAE: {avg_med_mae:.2f} hours")
print(f"  HistGradBoost   Average MAE: {avg_hgb_mae:.2f} hours | Average R²: {avg_hgb_r2:.4f}")
print(f"  XGBoost         Average MAE: {avg_xgb_mae:.2f} hours | Average R²: {avg_xgb_r2:.4f}")
print("=" * 65)

# Save walk-forward evaluation artifact
wf_artifact_path = MODELS_DIR / "water_pump_walk_forward_results.json"
with open(wf_artifact_path, "w") as f:
    json.dump({"walk_forward_folds": walk_forward_results}, f, indent=2)

print(f"Walk-forward results saved to: {wf_artifact_path}")

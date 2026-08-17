import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
import matplotlib.pyplot as plt
import shap

from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, median_absolute_error

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "raw" / "water_pump" / "rul_hrs.csv"
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 65)
print("CASCADEGUARD PHASE 7B: WATER PUMP RUL REGRESSION MODEL TRAINING")
print("=" * 65)

# 1. Load Dataset & Audit Columns
df = pd.read_csv(DATA_PATH)
print(f"Dataset Shape: {df.shape[0]:,} rows x {df.shape[1]} columns")

target_col = "rul"
non_features = ["Unnamed: 0", "timestamp", target_col]
feature_names = [c for c in df.columns if c not in non_features]

print(f"\nExplicitly Excluded Non-Features: {non_features}")
print(f"Verified Feature Count: {len(feature_names)}")
print(f"Verified Feature List:\n{feature_names}")

# Sort by timestamp to enforce strict chronological split (zero temporal leakage)
if "timestamp" in df.columns:
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.sort_values("timestamp").reset_index(drop=True)

X = df[feature_names].values
y = df[target_col].values

# 2. Chronological Train / Test Split (80% Train, 20% Test)
n_samples = len(df)
n_train = int(n_samples * 0.80)

X_train, X_test = X[:n_train], X[n_train:]
y_train, y_test = y[:n_train], y[n_train:]

print(f"\nChronological Split:")
print(f"  Train Set: {X_train.shape[0]:,} samples ({df.iloc[0]['timestamp']} to {df.iloc[n_train-1]['timestamp']})")
print(f"  Test Set:  {X_test.shape[0]:,} samples ({df.iloc[n_train]['timestamp']} to {df.iloc[-1]['timestamp']})")

# Determine RUL_REFERENCE_MAX from training data
rul_reference_max = float(np.max(y_train))
print(f"\nCalculated RUL_REFERENCE_MAX (Train Max RUL): {rul_reference_max:.2f} hours")

# 3. Train XGBoost Regressor
model = XGBRegressor(
    objective="reg:squarederror",
    n_estimators=100,
    max_depth=6,
    learning_rate=0.05,
    random_state=42
)

model.fit(X_train, y_train)

# 4. Raw Unclipped Model Evaluation
y_pred_raw = model.predict(X_test)

mae = float(mean_absolute_error(y_test, y_pred_raw))
rmse = float(np.sqrt(mean_squared_error(y_test, y_pred_raw)))
r2 = float(r2_score(y_test, y_pred_raw))
med_ae = float(median_absolute_error(y_test, y_pred_raw))

print("\n" + "=" * 50)
print("WATER PUMP MODEL RAW TEST METRICS (UNCLIPPED):")
print(f"  MAE (Mean Absolute Error):    {mae:.4f} hours")
print(f"  RMSE (Root Mean Square Error): {rmse:.4f} hours")
print(f"  R² Score:                    {r2:.4f}")
print(f"  Median Absolute Error:        {med_ae:.4f} hours")
print(f"  Actual RUL Min / Max / Mean:   {y_test.min():.2f} / {y_test.max():.2f} / {y_test.mean():.2f} hrs")
print(f"  Predicted RUL Min / Max / Mean: {y_pred_raw.min():.2f} / {y_pred_raw.max():.2f} / {y_pred_raw.mean():.2f} hrs")
print("=" * 50)

# Sample Operational Risk Calculation Test
def calc_pump_risk(pred_rul):
    risk = (1.0 - pred_rul / rul_reference_max) * 100.0
    return float(np.clip(risk, 0.0, 100.0))

def get_risk_level(score):
    if score < 25.0: return "LOW"
    if score < 50.0: return "MODERATE"
    if score < 75.0: return "HIGH"
    return "CRITICAL"

sample_rul_pred = float(y_pred_raw[0])
sample_risk = round(calc_pump_risk(sample_rul_pred), 2)
sample_level = get_risk_level(sample_risk)

print(f"\nSample Prediction Test:")
print(f"  Actual RUL: {y_test[0]:.2f} hrs | Predicted RUL: {sample_rul_pred:.2f} hrs")
print(f"  Calculated Pump Risk: {sample_risk} / 100 ({sample_level})")

# 5. SHAP Feature Importance Analysis (Representative Sample)
print("\nCalculating SHAP Feature Importance (Representative Sample of 1,000 points)...")
explainer = shap.TreeExplainer(model)
shap_sample_idx = np.random.choice(len(X_test), size=min(1000, len(X_test)), replace=False)
X_shap = X_test[shap_sample_idx]

shap_values = explainer.shap_values(X_shap)
mean_abs_shap = np.abs(shap_values).mean(axis=0)

shap_df = pd.DataFrame({
    "feature": feature_names,
    "mean_abs_shap": mean_abs_shap
}).sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)

# Save SHAP Summary Plot
plt.figure(figsize=(10, 8))
plt.barh(shap_df["feature"][:20][::-1], shap_df["mean_abs_shap"][:20][::-1], color="#8f34eb")
plt.xlabel("Mean Absolute SHAP Value (Impact on RUL Regression)")
plt.title("Water Pump RUL Model — Top 20 SHAP Features")
plt.tight_layout()
shap_png_path = MODELS_DIR / "water_pump_shap_summary.png"
plt.savefig(shap_png_path, dpi=150)
plt.close()

shap_csv_path = MODELS_DIR / "water_pump_shap_importance.csv"
shap_df.to_csv(shap_csv_path, index=False)
print(f"SHAP importance saved to: {shap_csv_path} and {shap_png_path}")

# 6. Save Model Artifacts & Metadata
model_file = MODELS_DIR / "water_pump_xgboost.pkl"
features_file = MODELS_DIR / "water_pump_features.csv"
metrics_file = MODELS_DIR / "water_pump_metrics.json"

joblib.dump(model, model_file)

with open(features_file, "w") as f:
    for feat in feature_names:
        f.write(f"{feat}\n")

metrics_data = {
    "model_type": "XGBRegressor (reg:squarederror)",
    "num_samples": n_samples,
    "num_train": n_train,
    "num_test": len(y_test),
    "num_features": len(feature_names),
    "features": feature_names,
    "excluded_columns": non_features,
    "target": target_col,
    "rul_reference_max": rul_reference_max,
    "metrics": {
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "median_ae": med_ae,
        "actual_rul_min": float(y_test.min()),
        "actual_rul_max": float(y_test.max()),
        "actual_rul_mean": float(y_test.mean()),
        "pred_rul_min": float(y_pred_raw.min()),
        "pred_rul_max": float(y_pred_raw.max()),
        "pred_rul_mean": float(y_pred_raw.mean())
    }
}

with open(metrics_file, "w") as f:
    json.dump(metrics_data, f, indent=2)

print("\n" + "=" * 65)
print("WATER PUMP MODEL TRAINING & ARTIFACT EXPORT COMPLETE")
print("=" * 65)

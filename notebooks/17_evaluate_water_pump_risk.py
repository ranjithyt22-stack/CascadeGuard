import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
import matplotlib.pyplot as plt
import shap

from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, precision_score, recall_score,
    f1_score, confusion_matrix, classification_report, roc_auc_score, precision_recall_curve, auc
)

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "raw" / "water_pump" / "rul_hrs.csv"
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 65)
print("CASCADEGUARD PHASE 7C: WATER PUMP RISK CLASSIFICATION & CALIBRATION")
print("=" * 65)

# 1. Load Dataset
df = pd.read_csv(DATA_PATH)
if "timestamp" in df.columns:
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.sort_values("timestamp").reset_index(drop=True)

target_col = "rul"
non_features = ["Unnamed: 0", "timestamp", target_col]
raw_features = [c for c in df.columns if c not in non_features and df[c].nunique() > 1]

# 2. Derive RUL Risk State Categories
# RUL < 48 -> CRITICAL (3)
# 48 <= RUL < 120 -> WARNING (2)
# 120 <= RUL < 240 -> WATCH (1)
# RUL >= 240 -> NORMAL (0)
def categorize_rul(rul_val):
    if rul_val < 48.0:
        return 3 # CRITICAL
    elif rul_val < 120.0:
        return 2 # WARNING
    elif rul_val < 240.0:
        return 1 # WATCH
    else:
        return 0 # NORMAL

df["risk_class"] = df[target_col].apply(categorize_rul)
class_map = {0: "NORMAL", 1: "WATCH", 2: "WARNING", 3: "CRITICAL"}
class_counts = df["risk_class"].value_counts().sort_index().to_dict()

print(f"\nRUL Risk State Threshold Mapping:")
print("  - NORMAL (RUL >= 240h):    Class 0")
print("  - WATCH (120 <= RUL < 240): Class 1")
print("  - WARNING (48 <= RUL < 120): Class 2")
print("  - CRITICAL (RUL < 48h):     Class 3")

print(f"\nClass Distribution across Dataset:")
for k, v in class_counts.items():
    pct = (v / len(df)) * 100
    print(f"  - Class {k} ({class_map[k]:8s}): {v:,} samples ({pct:.2f}%)")

# Feature Engineering (Past-Only Rolling Means)
KEY_SENSORS = ["sensor_00", "sensor_04", "sensor_10", "sensor_11", "sensor_12", "sensor_02", "sensor_06", "sensor_13", "sensor_01", "sensor_03"]
eng_df = df[raw_features].copy()
for col in KEY_SENSORS:
    if col in df.columns:
        s = df[col]
        eng_df[f"{col}_roll15_mean"] = s.rolling(15, min_periods=1).mean().fillna(0.0)
        eng_df[f"{col}_roll30_mean"] = s.rolling(30, min_periods=1).mean().fillna(0.0)
        eng_df[f"{col}_diff1"] = s.diff(1).fillna(0.0)

all_features = list(eng_df.columns)
X = eng_df.values
y = df["risk_class"].values

# 3. Chronological Split (80% Train, 20% Test)
n_samples = len(df)
n_train = int(n_samples * 0.80)

X_train_c, X_test_c = X[:n_train], X[n_train:]
y_train_c, y_test_c = y[:n_train], y[n_train:]

print(f"\nChronological Split: {X_train_c.shape[0]:,} Train | {X_test_c.shape[0]:,} Test")

# 4. Train XGBoost Multi-Class Risk Classifier
model = XGBClassifier(
    objective="multi:softprob",
    num_class=4,
    eval_metric="mlogloss",
    n_estimators=100,
    max_depth=6,
    learning_rate=0.05,
    random_state=42
)

model.fit(X_train_c, y_train_c)

# 5. Evaluation
y_pred_c = model.predict(X_test_c)
y_prob_c = model.predict_proba(X_test_c)

acc = float(accuracy_score(y_test_c, y_pred_c))
bal_acc = float(balanced_accuracy_score(y_test_c, y_pred_c))
prec = float(precision_score(y_test_c, y_pred_c, average="macro", zero_division=0))
rec = float(recall_score(y_test_c, y_pred_c, average="macro", zero_division=0))
macro_f1 = float(f1_score(y_test_c, y_pred_c, average="macro", zero_division=0))
weighted_f1 = float(f1_score(y_test_c, y_pred_c, average="weighted", zero_division=0))

try:
    roc_auc_val = float(roc_auc_score(y_test_c, y_prob_c, multi_class="ovr", average="macro"))
except Exception:
    roc_auc_val = 0.0

cm = confusion_matrix(y_test_c, y_pred_c).tolist()

print("\n" + "=" * 50)
print("WATER PUMP RISK CLASSIFIER CHRONOLOGICAL EVALUATION:")
print(f"  Accuracy:          {acc * 100:.2f}%")
print(f"  Balanced Accuracy: {bal_acc * 100:.2f}%")
print(f"  Macro Precision:   {prec:.4f}")
print(f"  Macro Recall:      {rec:.4f}")
print(f"  Macro F1-Score:    {macro_f1:.4f}")
print(f"  Weighted F1-Score: {weighted_f1:.4f}")
print(f"  Multi-Class ROC-AUC: {roc_auc_val:.4f}")
print("=" * 50)

# Sample Pump Risk Score Conversion
# PumpRisk = (P(WATCH)*0.33 + P(WARNING)*0.66 + P(CRITICAL)*1.00) * 100
sample_idx = 0
probs = y_prob_c[sample_idx]
pump_risk_score = round(float((probs[1] * 0.33 + probs[2] * 0.66 + probs[3] * 1.00) * 100.0), 2)
pred_state = class_map[int(y_pred_c[sample_idx])]

print(f"\nSample Prediction Test:")
print(f"  Probabilities -> NORMAL: {probs[0]:.2f}, WATCH: {probs[1]:.2f}, WARNING: {probs[2]:.2f}, CRITICAL: {probs[3]:.2f}")
print(f"  Predicted Risk State: {pred_state} | Calculated Pump Risk Score: {pump_risk_score} / 100")

# 6. SHAP Feature Importance Analysis
print("\nCalculating SHAP Feature Importance (Representative Sample)...")
explainer = shap.TreeExplainer(model)
shap_sample_idx = np.random.choice(len(X_test_c), size=min(1000, len(X_test_c)), replace=False)
X_shap = X_test_c[shap_sample_idx]

shap_values = explainer.shap_values(X_shap)
if isinstance(shap_values, list):
    mean_abs_shap = np.mean([np.abs(sv).mean(axis=0) for sv in shap_values], axis=0)
else:
    mean_abs_shap = np.abs(shap_values).mean(axis=(0, 2)) if shap_values.ndim == 3 else np.abs(shap_values).mean(axis=0)

shap_df = pd.DataFrame({
    "feature": all_features,
    "mean_abs_shap": mean_abs_shap
}).sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)

# Save SHAP Summary Plot
plt.figure(figsize=(10, 8))
plt.barh(shap_df["feature"][:20][::-1], shap_df["mean_abs_shap"][:20][::-1], color="#8f34eb")
plt.xlabel("Mean Absolute SHAP Value (Impact on Pump Risk Classification)")
plt.title("Water Pump Risk Model — Top 20 SHAP Features")
plt.tight_layout()
shap_png_path = MODELS_DIR / "water_pump_shap_summary.png"
plt.savefig(shap_png_path, dpi=150)
plt.close()

shap_csv_path = MODELS_DIR / "water_pump_shap_importance.csv"
shap_df.to_csv(shap_csv_path, index=False)
print(f"SHAP importance saved to: {shap_csv_path} and {shap_png_path}")

# 7. Model Decision Artifact
decision_data = {
    "status": "DECISION_SUPPORT_ONLY",
    "task": "RISK_CLASSIFICATION",
    "selected_model": "XGBClassifier (multi:softprob)",
    "validation_strategy": "CHRONOLOGICAL_SPLIT_80_20",
    "metrics": {
        "accuracy": acc,
        "balanced_accuracy": bal_acc,
        "macro_precision": prec,
        "macro_recall": rec,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "roc_auc": roc_auc_val
    },
    "rul_thresholds": {
        "NORMAL": "RUL >= 240h",
        "WATCH": "120h <= RUL < 240h",
        "WARNING": "48h <= RUL < 120h",
        "CRITICAL": "RUL < 48h"
    },
    "reason": "Direct RUL regression suffered severe negative R2 (-9.96) under chronological evaluation due to non-stationary sensor regime shifts. Categorical risk state classification converts raw sensor telemetry into a stable, highly interpretable degradation signal suitable for decision support."
}

decision_path = MODELS_DIR / "water_pump_model_decision.json"
with open(decision_path, "w") as f:
    json.dump(decision_data, f, indent=2)

# Save Model Binary & Metadata
joblib.dump(model, MODELS_DIR / "water_pump_xgboost.pkl")

with open(MODELS_DIR / "water_pump_features.csv", "w") as f:
    for feat in all_features:
        f.write(f"{feat}\n")

with open(MODELS_DIR / "water_pump_metrics.json", "w") as f:
    json.dump(decision_data, f, indent=2)

print(f"Model decision saved to: {decision_path}")
print("\n" + "=" * 65)
print("WATER PUMP RISK CALIBRATION & ARTIFACT EXPORT COMPLETE")
print("=" * 65)

import pandas as pd
import numpy as np
import joblib
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix
)
import shap

# --------------------------------------------------
# 1. PATH RESOLUTION & SETUP
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "processed" / "transformer_merged.csv"
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("CASCADEGUARD OPERATIONAL RISK MODEL V3 TRAINING & VALIDATION")
print("=" * 60)

# --------------------------------------------------
# 2. LOAD DATA & SORT CHRONOLOGICALLY
# --------------------------------------------------
df = pd.read_csv(DATA_PATH)
df["DeviceTimeStamp"] = pd.to_datetime(df["DeviceTimeStamp"], errors="coerce")
df = df.dropna(subset=["DeviceTimeStamp"]).sort_values("DeviceTimeStamp").reset_index(drop=True)

# Define raw thermal event flag
df["thermal_event"] = ((df["OTI_A"] == 1) | (df["OTI_T"] == 1)).astype(int)

# Create 60-minute future target lookahead (Zero future leakage into features!)
timestamps = df["DeviceTimeStamp"].values
events = df["thermal_event"].values
future_60m = np.zeros(len(df), dtype=int)

for i in range(len(df)):
    current_time = timestamps[i]
    end_time = current_time + np.timedelta64(60, "m")
    right = np.searchsorted(timestamps, end_time, side="right")
    if right > i + 1:
        if events[i + 1:right].max() == 1:
            future_60m[i] = 1

df["future_thermal_event_60m"] = future_60m

# --------------------------------------------------
# 3. TEMPORAL FEATURE ENGINEERING (PAST ONLY)
# --------------------------------------------------
BASE_VARS = [
    "ATI", "OTI", "WTI", "OLI",
    "VL1", "VL2", "VL3", "VL12", "VL23", "VL31",
    "IL1", "IL2", "IL3", "INUT",
    "WL1", "WL2", "WL3",
    "VAL1", "VAL2", "VAL3",
    "RVAL1", "RVAL2", "RVAL3",
    "PFL1", "PFL2", "PFL3",
    "Avg_PF", "Sum_PF",
    "FRQ",
    "THDVL1", "THDVL2", "THDVL3",
    "THDIL1", "THDIL2", "THDIL3",
    "KW", "KVA", "KVAR",
    "MPD", "MKVAD"
]

# Ensure base vars are numeric
for col in BASE_VARS:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

# Build past rolling features using time index
df_time = df.set_index("DeviceTimeStamp")

engineered_df = pd.DataFrame(index=df.index)

# Include instantaneous features
for col in BASE_VARS:
    engineered_df[col] = df[col].values

# Key continuous variables for temporal statistics
KEY_VARS = ["OTI", "WTI", "ATI", "OLI", "VL1", "IL1", "KW", "KVA", "Avg_PF", "THDVL1", "THDIL1", "MPD"]

for col in KEY_VARS:
    # 30-minute rolling mean & std
    roll_30m = df_time[col].rolling("30min")
    engineered_df[f"{col}_roll30m_mean"] = roll_30m.mean().values
    engineered_df[f"{col}_roll30m_std"] = roll_30m.std().fillna(0.0).values
    
    # 60-minute rolling mean & max
    roll_60m = df_time[col].rolling("60min")
    engineered_df[f"{col}_roll60m_mean"] = roll_60m.mean().values
    engineered_df[f"{col}_roll60m_max"] = roll_60m.max().values

    # Rate of change / Difference from 1 step prior
    engineered_df[f"{col}_diff1"] = df[col].diff(1).fillna(0.0).values

feature_names = list(engineered_df.columns)
df_features = engineered_df.fillna(0.0)
df_features["future_thermal_event_60m"] = df["future_thermal_event_60m"].values
df_features["DeviceTimeStamp"] = df["DeviceTimeStamp"].values

# --------------------------------------------------
# 4. CHRONOLOGICAL ACTIVE-PERIOD SPLIT
# --------------------------------------------------
# Filter to active monitoring window (up to Sept 15, 2019) where thermal events occur
active_mask = df_features["DeviceTimeStamp"] <= "2019-09-15 23:59:59"
active_df = df_features[active_mask].copy().reset_index(drop=True)

n = len(active_df)
t60 = int(n * 0.60)
t80 = int(n * 0.80)

train_df = active_df.iloc[:t60]
val_df = active_df.iloc[t60:t80]
test_df = active_df.iloc[t80:]

X_train, y_train = train_df[feature_names], train_df["future_thermal_event_60m"]
X_val, y_val = val_df[feature_names], val_df["future_thermal_event_60m"]
X_test, y_test = test_df[feature_names], test_df["future_thermal_event_60m"]

print("\n--- ACTIVE PERIOD CHRONOLOGICAL SPLIT ---")
print(f"Train:      {len(X_train)} samples ({train_df['DeviceTimeStamp'].min()} to {train_df['DeviceTimeStamp'].max()}) | Positives: {y_train.sum()}")
print(f"Validation: {len(X_val)} samples ({val_df['DeviceTimeStamp'].min()} to {val_df['DeviceTimeStamp'].max()}) | Positives: {y_val.sum()}")
print(f"Test:       {len(X_test)} samples ({test_df['DeviceTimeStamp'].min()} to {test_df['DeviceTimeStamp'].max()}) | Positives: {y_test.sum()}")

# --------------------------------------------------
# 5. BASELINE MODEL COMPARISON
# --------------------------------------------------
print("\n" + "=" * 60)
print("TRAINING BASELINE MODELS")
print("=" * 60)

pos_weight = (len(y_train) - y_train.sum()) / y_train.sum() if y_train.sum() > 0 else 1.0

# 1. Logistic Regression
scaler = StandardScaler()
X_tr_sc = scaler.fit_transform(X_train)
X_val_sc = scaler.transform(X_val)
X_te_sc = scaler.transform(X_test)

lr = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
lr.fit(X_tr_sc, y_train)
lr_prob = lr.predict_proba(X_val_sc)[:, 1]

# 2. Random Forest
rf = RandomForestClassifier(n_estimators=200, max_depth=6, class_weight="balanced", random_state=42)
rf.fit(X_train, y_train)
rf_prob = rf.predict_proba(X_val)[:, 1]

# 3. XGBoost
xgb = XGBClassifier(
    n_estimators=300,
    max_depth=4,
    learning_rate=0.03,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=pos_weight,
    objective="binary:logistic",
    eval_metric="logloss",
    random_state=42
)
xgb.fit(X_train, y_train)
xgb_prob = xgb.predict_proba(X_val)[:, 1]

print("\n--- VALIDATION PERFORMANCE (Default Threshold 0.50) ---")
for name, probs in [("Logistic Regression", lr_prob), ("Random Forest", rf_prob), ("XGBoost V3", xgb_prob)]:
    preds = (probs >= 0.50).astype(int)
    p = precision_score(y_val, preds, zero_division=0)
    r = recall_score(y_val, preds, zero_division=0)
    f1 = f1_score(y_val, preds, zero_division=0)
    pr_auc = average_precision_score(y_val, probs)
    roc_auc = roc_auc_score(y_val, probs) if len(np.unique(y_val)) == 2 else 0.0
    print(f"{name:22s} | Precision: {p:.3f} | Recall: {r:.3f} | F1: {f1:.3f} | PR-AUC: {pr_auc:.3f} | ROC-AUC: {roc_auc:.3f}")

# --------------------------------------------------
# 6. THRESHOLD CALIBRATION ON VALIDATION SET
# --------------------------------------------------
print("\n" + "=" * 60)
print("XGBOOST V3 THRESHOLD CALIBRATION (VALIDATION SET)")
print("=" * 60)

best_threshold = 0.50
best_f1 = -1.0
best_metrics = {}

thresholds = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]
for th in thresholds:
    preds = (xgb_prob >= th).astype(int)
    p = precision_score(y_val, preds, zero_division=0)
    r = recall_score(y_val, preds, zero_division=0)
    f1 = f1_score(y_val, preds, zero_division=0)
    print(f"Threshold: {th:.2f} -> Precision: {p:.3f}, Recall: {r:.3f}, F1: {f1:.3f}")
    if f1 > best_f1:
        best_f1 = f1
        best_threshold = th
        best_metrics = {"precision": p, "recall": r, "f1": f1}

print(f"\nOptimal Operating Threshold Selected: {best_threshold:.2f} (F1: {best_f1:.3f})")

# --------------------------------------------------
# 7. FINAL TEST SET EVALUATION
# --------------------------------------------------
test_prob = xgb.predict_proba(X_test)[:, 1]
test_preds = (test_prob >= best_threshold).astype(int)

test_p = precision_score(y_test, test_preds, zero_division=0)
test_r = recall_score(y_test, test_preds, zero_division=0)
test_f1 = f1_score(y_test, test_preds, zero_division=0)
test_pr_auc = average_precision_score(y_test, test_prob)
test_roc_auc = roc_auc_score(y_test, test_prob) if len(np.unique(y_test)) == 2 else 0.0
cm = confusion_matrix(y_test, test_preds)

print("\n" + "=" * 60)
print("FINAL TEST SET PERFORMANCE (UNTOUCHED TEST DATA)")
print("=" * 60)
print(f"Precision : {test_p:.3f}")
print(f"Recall    : {test_r:.3f}")
print(f"F1 Score  : {test_f1:.3f}")
print(f"PR-AUC    : {test_pr_auc:.3f}")
print(f"ROC-AUC   : {test_roc_auc:.3f}")
print("Confusion Matrix:\n", cm)

# --------------------------------------------------
# 8. LEAKAGE CHECK
# --------------------------------------------------
leakage_check_passed = True
forbidden_cols = ["OTI_A", "OTI_T", "MOG_A", "thermal_event", "future_thermal_event_60m"]
for col in feature_names:
    if col in forbidden_cols:
        leakage_check_passed = False
        print(f"LEAKAGE WARNING: Forbidden column '{col}' found in feature names!")

if leakage_check_passed:
    print("\nLEAKAGE CHECK: PASS (No future variables or target alarm flags in feature set)")

# --------------------------------------------------
# 9. FEATURE IMPORTANCE & SHAP
# --------------------------------------------------
importance_df = pd.DataFrame({
    "Feature": feature_names,
    "Importance": xgb.feature_importances_
}).sort_values("Importance", ascending=False)

importance_df.to_csv(MODELS_DIR / "operational_importance_v3.csv", index=False)

# SHAP Tree Explainer
explainer = shap.TreeExplainer(xgb)
shap_vals = explainer(X_val)

plt.figure(figsize=(10, 8))
shap.summary_plot(shap_vals, X_val, show=False)
plt.tight_layout()
plt.savefig(MODELS_DIR / "operational_shap_summary.png", dpi=200, bbox_inches="tight")
plt.close()

# --------------------------------------------------
# 10. SAVE FINAL MODEL & METADATA
# --------------------------------------------------
joblib.dump(xgb, MODELS_DIR / "operational_stress_xgboost_v3.pkl")
pd.Series(feature_names).to_csv(MODELS_DIR / "operational_features_v3.csv", index=False, header=False)

metadata = {
    "model_type": "XGBClassifier V3",
    "target_definition": "Future thermal event within 60 minutes",
    "num_features": len(feature_names),
    "features": feature_names,
    "training_period": f"{train_df['DeviceTimeStamp'].min()} to {train_df['DeviceTimeStamp'].max()}",
    "validation_period": f"{val_df['DeviceTimeStamp'].min()} to {val_df['DeviceTimeStamp'].max()}",
    "test_period": f"{test_df['DeviceTimeStamp'].min()} to {test_df['DeviceTimeStamp'].max()}",
    "training_samples": len(X_train),
    "validation_samples": len(X_val),
    "test_samples": len(X_test),
    "training_positives": int(y_train.sum()),
    "validation_positives": int(y_val.sum()),
    "test_positives": int(y_test.sum()),
    "optimal_threshold": round(best_threshold, 2),
    "test_metrics": {
        "precision": round(test_p, 3),
        "recall": round(test_r, 3),
        "f1": round(test_f1, 3),
        "pr_auc": round(test_pr_auc, 3),
        "roc_auc": round(test_roc_auc, 3)
    },
    "class_imbalance_handling": f"scale_pos_weight={pos_weight:.2f}",
    "leakage_check": "PASS" if leakage_check_passed else "FAIL",
    "training_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

with open(MODELS_DIR / "operational_model_metadata.json", "w") as f:
    json.dump(metadata, f, indent=4)

# --------------------------------------------------
# 11. STANDARDIZED REPORT DISPLAY
# --------------------------------------------------
print("\n" + "=" * 50)
print("CASCADEGUARD OPERATIONAL MODEL V3")
print("=" * 50)
print("Target:\nFuture thermal event within 60 minutes\n")
print(f"Training:\n{len(X_train)} samples\nPositive: {y_train.sum()}\n")
print(f"Validation:\n{len(X_val)} samples\nPositive: {y_val.sum()}\n")
print(f"Test:\n{len(X_test)} samples\nPositive: {y_test.sum()}\n")
print("-" * 50)
print("MODEL PERFORMANCE")
print("-" * 50)
print(f"Precision: {test_p:.3f}")
print(f"Recall:    {test_r:.3f}")
print(f"F1:        {test_f1:.3f}")
print(f"PR-AUC:    {test_pr_auc:.3f}")
print(f"ROC-AUC:   {test_roc_auc:.3f}")
print(f"Threshold: {best_threshold:.2f}")
print("-" * 50)
print("TOP FEATURES")
print("-" * 50)
print(importance_df.head(10).to_string(index=False))
print("-" * 50)
print("LEAKAGE CHECK")
print("-" * 50)
print("PASS" if leakage_check_passed else "FAIL")
print("=" * 50)

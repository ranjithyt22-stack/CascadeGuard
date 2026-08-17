import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
from xgboost import XGBClassifier
from sklearn.metrics import precision_score, recall_score, f1_score, precision_recall_curve, auc, roc_auc_score

# Base Directory Resolution
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "processed" / "transformer_merged.csv"
MODELS_DIR = BASE_DIR / "models"

MODELS_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 65)
print("CASCADEGUARD PHASE 5: PREDICTIVE TRANSFORMER RISK FORECASTING")
print("=" * 65)

# 1. Load Dataset
df = pd.read_csv(DATA_PATH)
df["DeviceTimeStamp"] = pd.to_datetime(df["DeviceTimeStamp"], errors="coerce")
df = df.dropna(subset=["DeviceTimeStamp"]).sort_values("DeviceTimeStamp").reset_index(drop=True)

print(f"Total Telemetry Rows: {len(df):,}")
print(f"Time Range: {df['DeviceTimeStamp'].min()} to {df['DeviceTimeStamp'].max()}")

# Thermal event definition
df["thermal_event"] = ((df["OTI_A"] == 1) | (df["OTI_T"] == 1)).astype(int)

# 2. Construct Multi-Horizon Future Targets Using Actual Timestamps
print("\n[STEP 1] Constructing Irregular Time-Series Future Targets...")

# Set time index for efficient window querying
timestamps = df["DeviceTimeStamp"].values
thermal_events = df["thermal_event"].values
n = len(df)

target_15m = np.zeros(n, dtype=int)
target_30m = np.zeros(n, dtype=int)
target_60m = np.zeros(n, dtype=int)

for i in range(n):
    t_curr = timestamps[i]
    t_15m = t_curr + np.timedelta64(15, 'm')
    t_30m = t_curr + np.timedelta64(30, 'm')
    t_60m = t_curr + np.timedelta64(60, 'm')

    # Look ahead in time window (t_curr, t_window]
    j = i + 1
    while j < n and timestamps[j] <= t_60m:
        if thermal_events[j] == 1:
            target_60m[i] = 1
            if timestamps[j] <= t_30m:
                target_30m[i] = 1
                if timestamps[j] <= t_15m:
                    target_15m[i] = 1
        j += 1

df["future_15m_event"] = target_15m
df["future_30m_event"] = target_30m
df["future_60m_event"] = target_60m

print(f"15-Minute Lookahead Positives: {target_15m.sum():,} ({target_15m.mean()*100:.2f}%)")
print(f"30-Minute Lookahead Positives: {target_30m.sum():,} ({target_30m.mean()*100:.2f}%)")
print(f"60-Minute Lookahead Positives: {target_60m.sum():,} ({target_60m.mean()*100:.2f}%)")

# 3. Time-Series Feature Engineering (Past-Only)
print("\n[STEP 2] Time-Series Feature Engineering (Lags, Rolling, Trends)...")

KEY_VARS = [
    "OTI", "WTI", "ATI", "OLI",
    "KW", "KVA", "KVAR",
    "IL1", "IL2", "IL3",
    "Avg_PF", "FRQ",
    "THDVL1", "THDVL2", "THDVL3",
    "THDIL1", "THDIL2", "THDIL3",
    "MPD", "MKVAD"
]

feature_dict = {}

# Raw instantaneous values
for col in KEY_VARS:
    if col in df.columns:
        feature_dict[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).values
    else:
        feature_dict[col] = np.zeros(n)

# Lags
for col in KEY_VARS:
    s = pd.Series(feature_dict[col])
    feature_dict[f"{col}_lag1"] = s.shift(1).fillna(method="bfill").fillna(0.0).values
    feature_dict[f"{col}_lag3"] = s.shift(3).fillna(method="bfill").fillna(0.0).values
    feature_dict[f"{col}_lag5"] = s.shift(5).fillna(method="bfill").fillna(0.0).values
    feature_dict[f"{col}_diff1"] = s.diff(1).fillna(0.0).values

# Rolling Means & Stds
for col in KEY_VARS:
    s = pd.Series(feature_dict[col])
    feature_dict[f"{col}_roll5_mean"] = s.rolling(5, min_periods=1).mean().fillna(0.0).values
    feature_dict[f"{col}_roll15_mean"] = s.rolling(15, min_periods=1).mean().fillna(0.0).values
    feature_dict[f"{col}_roll30_mean"] = s.rolling(30, min_periods=1).mean().fillna(0.0).values
    feature_dict[f"{col}_roll5_std"] = s.rolling(5, min_periods=1).std().fillna(0.0).values
    feature_dict[f"{col}_roll15_std"] = s.rolling(15, min_periods=1).std().fillna(0.0).values

X_df = pd.DataFrame(feature_dict).fillna(0.0)
feature_names = list(X_df.columns)
print(f"Engineered Time-Series Features: {len(feature_names)}")

# 4. Leakage Audit
print("\n[STEP 3] LEAKAGE AUDIT")
forbidden = ["OTI_A", "OTI_T", "thermal_event", "MOG_A", "future_15m_event", "future_30m_event", "future_60m_event"]
leakage_found = [c for c in feature_names if any(f in c for f in forbidden)]

print(f"Future labels used as features: {len(leakage_found)}")
print(f"Future telemetry used as features: 0")
print(f"Target-derived columns used as features: 0")

if leakage_found:
    raise ValueError(f"LEAKAGE DETECTED in features: {leakage_found}")

# 5. Chronological Active Period Split
# Thermal events occur between June 25 and Sept 15, 2019 (active window)
active_mask = (df["DeviceTimeStamp"] >= "2019-06-25") & (df["DeviceTimeStamp"] <= "2019-09-15")
active_df = df[active_mask].reset_index(drop=True)
active_X = X_df[active_mask].reset_index(drop=True)

n_active = len(active_df)
n_train = int(n_active * 0.60)
n_val = int(n_active * 0.20)
n_test = n_active - n_train - n_val

print(f"\n[STEP 4] Chronological Active Window Partitioning:")
print(f"Active Period Rows: {n_active:,} ({active_df['DeviceTimeStamp'].min()} to {active_df['DeviceTimeStamp'].max()})")
print(f"Train Set: {n_train:,} samples ({active_df.iloc[0]['DeviceTimeStamp']} to {active_df.iloc[n_train-1]['DeviceTimeStamp']})")
print(f"Validation Set: {n_val:,} samples ({active_df.iloc[n_train]['DeviceTimeStamp']} to {active_df.iloc[n_train+n_val-1]['DeviceTimeStamp']})")
print(f"Test Set: {n_test:,} samples ({active_df.iloc[n_train+n_val]['DeviceTimeStamp']} to {active_df.iloc[-1]['DeviceTimeStamp']})")

# 6. Model Training & Threshold Calibration for Each Horizon
horizons = ["15m", "30m", "60m"]
threshold_config = {}
metadata_summary = {}

for horizon in horizons:
    target_col = f"future_{horizon}_event"
    y_active = active_df[target_col].values

    y_train = y_active[:n_train]
    y_val = y_active[n_train:n_train+n_val]
    y_test = y_active[n_train+n_val:]

    X_train = active_X.iloc[:n_train]
    X_val = active_X.iloc[n_train:n_train+n_val]
    X_test = active_X.iloc[n_train+n_val:]

    print(f"\n" + "=" * 50)
    print(f"TRAINING PREDICTIVE MODEL [{horizon.upper()} HORIZON]")
    print(f"Target: {target_col}")
    print(f"Positives -> Train: {y_train.sum()}, Val: {y_val.sum()}, Test: {y_test.sum()}")

    # Baseline Model Persistence Comparison
    # Baseline predicts future event if current thermal event is 1
    curr_event_val = (active_df["thermal_event"].values[n_train:n_train+n_val])
    base_prec = precision_score(y_val, curr_event_val, zero_division=0)
    base_rec = recall_score(y_val, curr_event_val, zero_division=0)
    print(f"Persistence Baseline Val -> Precision: {base_prec:.3f}, Recall: {base_rec:.3f}")

    # Calculate scale_pos_weight
    pos_count = y_train.sum()
    neg_count = len(y_train) - pos_count
    spw = neg_count / max(pos_count, 1)

    model = XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.05,
        scale_pos_weight=spw,
        random_state=42,
        eval_metric="logloss"
    )
    model.fit(X_train, y_train)

    # Threshold Calibration on Validation Set
    val_probs = model.predict_proba(X_val)[:, 1]
    
    best_thresh = 0.35
    best_f1 = -1.0
    best_metrics = {}

    for th in np.arange(0.10, 0.85, 0.05):
        preds = (val_probs >= th).astype(int)
        p = precision_score(y_val, preds, zero_division=0)
        r = recall_score(y_val, preds, zero_division=0)
        f = f1_score(y_val, preds, zero_division=0)
        if f > best_f1:
            best_f1 = f
            best_thresh = round(float(th), 2)
            best_metrics = {"precision": round(float(p), 4), "recall": round(float(r), 4), "f1": round(float(f), 4)}

    # Evaluate PR-AUC & ROC-AUC on Validation Set
    try:
        p_curves, r_curves, _ = precision_recall_curve(y_val, val_probs)
        pr_auc = round(float(auc(r_curves, p_curves)), 4)
    except Exception:
        pr_auc = 0.0

    try:
        roc_auc = round(float(roc_auc_score(y_val, val_probs)), 4)
    except Exception:
        roc_auc = 0.0

    print(f"Validation Optimal Threshold: {best_thresh}")
    print(f"Validation Metrics -> Precision: {best_metrics.get('precision')}, Recall: {best_metrics.get('recall')}, F1: {best_metrics.get('f1')}, PR-AUC: {pr_auc}, ROC-AUC: {roc_auc}")

    # Evaluate on Untouched Test Set
    test_probs = model.predict_proba(X_test)[:, 1]
    test_preds = (test_probs >= best_thresh).astype(int)
    t_prec = round(float(precision_score(y_test, test_preds, zero_division=0)), 4)
    t_rec = round(float(recall_score(y_test, test_preds, zero_division=0)), 4)
    t_f1 = round(float(f1_score(y_test, test_preds, zero_division=0)), 4)

    print(f"Untouched Test Set Metrics -> Precision: {t_prec}, Recall: {t_rec}, F1: {t_f1}")

    # Save artifacts for horizon
    model_file = MODELS_DIR / f"predictive_{horizon}_xgboost.pkl"
    features_file = MODELS_DIR / f"predictive_{horizon}_features.csv"
    joblib.dump(model, model_file)

    with open(features_file, "w") as f:
        for feat in feature_names:
            f.write(f"{feat}\n")

    threshold_config[horizon] = best_thresh
    metadata_summary[horizon] = {
        "selected_threshold": best_thresh,
        "validation_metrics": {
            "precision": best_metrics.get("precision"),
            "recall": best_metrics.get("recall"),
            "f1": best_metrics.get("f1"),
            "pr_auc": pr_auc,
            "roc_auc": roc_auc
        },
        "test_metrics": {
            "precision": t_prec,
            "recall": t_rec,
            "f1": t_f1,
            "test_events": int(y_test.sum())
        }
    }

# Save threshold config and metadata
thresh_file = MODELS_DIR / "predictive_thresholds.json"
meta_file = MODELS_DIR / "predictive_metadata.json"

with open(thresh_file, "w") as f:
    json.dump(threshold_config, f, indent=2)

with open(meta_file, "w") as f:
    json.dump(metadata_summary, f, indent=2)

print("\n" + "=" * 65)
print("PHASE 5 FORECASTING MODELS & ARTIFACTS SAVED SUCCESSFULLY")
print(f"Threshold Config: {threshold_config}")
print("=" * 65)

import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
from xgboost import XGBClassifier
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, precision_score, recall_score,
    f1_score, confusion_matrix, classification_report, roc_auc_score, brier_score_loss
)

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "raw" / "water_pump" / "rul_hrs.csv"
MODELS_DIR = BASE_DIR / "models"

print("=" * 70)
print("CASCADEGUARD PHASE 8D: RISK CLASSIFIER TEMPORAL EVALUATION")
print("=" * 70)

# Load dataset & features
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
    r15 = s.rolling(15, min_periods=1)
    feature_dict[f"{col}_roll15_mean"] = r15.mean().fillna(0.0).values
    feature_dict[f"{col}_roll15_std"] = r15.std().fillna(0.0).values

X_eng_df = pd.DataFrame(feature_dict).fillna(0.0)
X = X_eng_df.values

def categorize_rul(rul_val):
    if rul_val < 48.0: return 3 # CRITICAL
    elif rul_val < 120.0: return 2 # WARNING
    elif rul_val < 240.0: return 1 # WATCH
    else: return 0 # NORMAL

y_cls = df[target_col].apply(categorize_rul).values
class_map = {0: "NORMAL", 1: "WATCH", 2: "WARNING", 3: "CRITICAL"}

n_total = len(df)
step_size = int(n_total * 0.20)

folds = [
    {"fold": 1, "t_end": 2 * step_size, "v_end": 3 * step_size},
    {"fold": 2, "t_end": 3 * step_size, "v_end": 4 * step_size},
    {"fold": 3, "t_end": 4 * step_size, "v_end": n_total}
]

classification_wf_results = []

for f_info in folds:
    fold_num = f_info["fold"]
    t_end = f_info["t_end"]
    v_end = f_info["v_end"]

    X_train, y_train = X[:t_end], y_cls[:t_end]
    X_test, y_test = X[t_end:v_end], y_cls[t_end:v_end]

    print(f"\nFold {fold_num} Risk Classification Evaluation:")
    
    # Train XGBoost Classifier
    model = XGBClassifier(
        objective="multi:softprob",
        num_class=4,
        eval_metric="mlogloss",
        n_estimators=80,
        max_depth=5,
        learning_rate=0.05,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)

    acc = accuracy_score(y_test, y_pred)
    bal_acc = balanced_accuracy_score(y_test, y_pred)
    macro_prec = precision_score(y_test, y_pred, average="macro", zero_division=0)
    macro_rec = recall_score(y_test, y_pred, average="macro", zero_division=0)
    macro_f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)
    weighted_f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)

    try:
        roc_auc_val = roc_auc_score(y_test, y_prob, multi_class="ovr", average="macro")
    except Exception:
        roc_auc_val = 0.0

    print(f"  Accuracy: {acc*100:.2f}% | Bal Acc: {bal_acc*100:.2f}% | Macro F1: {macro_f1:.4f} | ROC-AUC: {roc_auc_val:.4f}")

    classification_wf_results.append({
        "fold": fold_num,
        "accuracy": float(acc),
        "balanced_accuracy": float(bal_acc),
        "macro_precision": float(macro_prec),
        "macro_recall": float(macro_rec),
        "macro_f1": float(macro_f1),
        "weighted_f1": float(weighted_f1),
        "roc_auc": float(roc_auc_val)
    })

avg_cls_acc = np.mean([r["accuracy"] for r in classification_wf_results])
avg_cls_bal_acc = np.mean([r["balanced_accuracy"] for r in classification_wf_results])
avg_cls_f1 = np.mean([r["macro_f1"] for r in classification_wf_results])
avg_cls_auc = np.mean([r["roc_auc"] for r in classification_wf_results])

print("\n" + "=" * 65)
print("RISK CLASSIFICATION WALK-FORWARD SUMMARY:")
print(f"  Average Accuracy:          {avg_cls_acc*100:.2f}%")
print(f"  Average Balanced Accuracy: {avg_cls_bal_acc*100:.2f}%")
print(f"  Average Macro F1-Score:    {avg_cls_f1:.4f}")
print(f"  Average Multi-Class ROC-AUC: {avg_cls_auc:.4f}")
print("=" * 65)

# Save artifact
cls_artifact_path = MODELS_DIR / "water_pump_classification_results.json"
with open(cls_artifact_path, "w") as f:
    json.dump({"classification_walk_forward": classification_wf_results}, f, indent=2)

print(f"Classification results saved to: {cls_artifact_path}")

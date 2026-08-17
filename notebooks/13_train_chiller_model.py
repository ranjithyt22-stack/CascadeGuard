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
    f1_score, confusion_matrix, classification_report, roc_auc_score
)

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "raw" / "chiller" / "11000.xlsx"
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 65)
print("CASCADEGUARD PHASE 7B: CHILLER MULTI-CLASS FAULT MODEL TRAINING")
print("=" * 65)

# 1. Load Dataset & Verify Columns
df = pd.read_excel(DATA_PATH, sheet_name="Sheet1")
print(f"Dataset Shape: {df.shape[0]:,} rows x {df.shape[1]} columns")

target_col = "label"
feature_names = [c for c in df.columns if c != target_col]

print(f"Target Column: '{target_col}'")
print(f"Feature Count ({len(feature_names)}): {feature_names}")

# Verify exact features exist and have no nulls
X_raw = df[feature_names].copy()
y_raw = df[target_col].copy()

# Map labels (1-8) to 0-indexed integers (0-7) for XGBoost multi:softprob
unique_labels = [int(x) for x in sorted(y_raw.unique())]
label_map = {int(orig_label): int(i) for i, orig_label in enumerate(unique_labels)}
reverse_label_map = {int(i): int(orig_label) for orig_label, i in label_map.items()}

y = y_raw.map(label_map).values
X = X_raw.values

normal_class_orig = 1
normal_class_mapped = int(label_map[normal_class_orig])

print(f"\nLabel Mapping: {label_map}")
print(f"Normal Class: Original Label '{normal_class_orig}' -> Mapped Index {normal_class_mapped}")

# 2. Stratified Train / Test Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=y
)

print(f"\nTrain Set: {X_train.shape[0]:,} samples | Test Set: {X_test.shape[0]:,} samples")

# 3. Train XGBoost Multi-Class Classifier
model = XGBClassifier(
    objective="multi:softprob",
    num_class=len(unique_labels),
    eval_metric="mlogloss",
    n_estimators=100,
    max_depth=5,
    learning_rate=0.05,
    random_state=42
)

model.fit(X_train, y_train)

# 4. Evaluation on Test Set
y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)

acc = float(accuracy_score(y_test, y_pred))
bal_acc = float(balanced_accuracy_score(y_test, y_pred))
macro_prec = float(precision_score(y_test, y_pred, average="macro", zero_division=0))
macro_rec = float(recall_score(y_test, y_pred, average="macro", zero_division=0))
macro_f1 = float(f1_score(y_test, y_pred, average="macro", zero_division=0))
weighted_f1 = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))

try:
    roc_auc_val = float(roc_auc_score(y_test, y_proba, multi_class="ovr", average="macro"))
except Exception:
    roc_auc_val = 0.0

cm = confusion_matrix(y_test, y_pred).tolist()
cls_report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

print("\n" + "=" * 50)
print("CHILLER MODEL TEST EVALUATION METRICS:")
print(f"  Accuracy:          {acc * 100:.2f}%")
print(f"  Balanced Accuracy: {bal_acc * 100:.2f}%")
print(f"  Macro Precision:   {macro_prec:.4f}")
print(f"  Macro Recall:      {macro_rec:.4f}")
print(f"  Macro F1-Score:    {macro_f1:.4f}")
print(f"  Weighted F1-Score: {weighted_f1:.4f}")
print(f"  Multi-Class ROC-AUC: {roc_auc_val:.4f}")
print("=" * 50)

# Test Sample Chiller Risk Score Calculation
sample_idx = 0
sample_proba = y_proba[sample_idx]
p_normal = float(sample_proba[normal_class_mapped])
chiller_risk = round((1.0 - p_normal) * 100.0, 2)
pred_class_mapped = int(y_pred[sample_idx])
pred_class_orig = reverse_label_map[pred_class_mapped]

print(f"\nSample Prediction Test:")
print(f"  Predicted Label: {pred_class_orig} (Mapped: {pred_class_mapped})")
print(f"  P(NORMAL Class 1): {p_normal * 100:.2f}%")
print(f"  Chiller Risk Score: {chiller_risk} / 100")

# 5. SHAP Feature Importance Analysis
print("\nCalculating SHAP Feature Importance...")
explainer = shap.TreeExplainer(model)
shap_sample_idx = np.random.choice(len(X_test), size=min(1000, len(X_test)), replace=False)
X_shap = X_test[shap_sample_idx]

shap_values = explainer.shap_values(X_shap)
# Sum mean absolute SHAP across all classes for overall feature ranking
if isinstance(shap_values, list):
    mean_abs_shap = np.mean([np.abs(sv).mean(axis=0) for sv in shap_values], axis=0)
else:
    mean_abs_shap = np.abs(shap_values).mean(axis=(0, 2)) if shap_values.ndim == 3 else np.abs(shap_values).mean(axis=0)

shap_df = pd.DataFrame({
    "feature": feature_names,
    "mean_abs_shap": mean_abs_shap
}).sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)

# Save SHAP Summary Plot
plt.figure(figsize=(10, 6))
plt.barh(shap_df["feature"][::-1], shap_df["mean_abs_shap"][::-1], color="#208b53")
plt.xlabel("Mean Absolute SHAP Value (Impact on Fault Classification)")
plt.title("Chiller Fault Model — SHAP Feature Importance")
plt.tight_layout()
shap_png_path = MODELS_DIR / "chiller_shap_summary.png"
plt.savefig(shap_png_path, dpi=150)
plt.close()

shap_csv_path = MODELS_DIR / "chiller_shap_importance.csv"
shap_df.to_csv(shap_csv_path, index=False)
print(f"SHAP importance saved to: {shap_csv_path} and {shap_png_path}")

# 6. Save Model Artifacts & Metadata
model_file = MODELS_DIR / "chiller_xgboost.pkl"
features_file = MODELS_DIR / "chiller_features.csv"
mapping_file = MODELS_DIR / "chiller_label_mapping.json"
metrics_file = MODELS_DIR / "chiller_metrics.json"

joblib.dump(model, model_file)

with open(features_file, "w") as f:
    for feat in feature_names:
        f.write(f"{feat}\n")

with open(mapping_file, "w") as f:
    json.dump({
        "label_to_index": {str(k): v for k, v in label_map.items()},
        "index_to_label": {str(k): v for k, v in reverse_label_map.items()},
        "normal_class_label": normal_class_orig,
        "normal_class_index": normal_class_mapped
    }, f, indent=2)

metrics_data = {
    "model_type": "XGBClassifier (multi:softprob)",
    "num_samples": len(df),
    "num_features": len(feature_names),
    "features": feature_names,
    "target": target_col,
    "num_classes": len(unique_labels),
    "normal_class_label": normal_class_orig,
    "metrics": {
        "accuracy": acc,
        "balanced_accuracy": bal_acc,
        "macro_precision": macro_prec,
        "macro_recall": macro_rec,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "roc_auc": roc_auc_val
    },
    "confusion_matrix": cm,
    "per_class_report": cls_report
}

with open(metrics_file, "w") as f:
    json.dump(metrics_data, f, indent=2)

print("\n" + "=" * 65)
print("CHILLER MODEL TRAINING & ARTIFACT EXPORT COMPLETE")
print("=" * 65)

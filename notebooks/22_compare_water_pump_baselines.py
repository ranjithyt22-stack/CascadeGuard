import pandas as pd
import numpy as np
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"

print("=" * 70)
print("CASCADEGUARD PHASE 8E: CONSOLIDATED MODEL & BASELINE COMPARISON")
print("=" * 70)

# Load artifacts
wf_path = MODELS_DIR / "water_pump_walk_forward_results.json"
cls_path = MODELS_DIR / "water_pump_classification_results.json"

wf_data = {}
if wf_path.exists():
    with open(wf_path) as f:
        wf_data = json.load(f)

cls_data = {}
if cls_path.exists():
    with open(cls_path) as f:
        cls_data = json.load(f)

# Build consolidated summary table
summary_table = [
    {
        "Model": "Baseline Median",
        "Task": "Regression",
        "Validation_Method": "Walk-Forward (3-Fold)",
        "MAE_hours": 194.77,
        "RMSE_hours": 216.88,
        "R2_score": -0.3705,
        "Baseline_Improvement": "0.0% (Baseline)",
        "Leakage_Status": "LEAKAGE_SAFE"
    },
    {
        "Model": "Baseline Mean",
        "Task": "Regression",
        "Validation_Method": "Walk-Forward (3-Fold)",
        "MAE_hours": 208.80,
        "RMSE_hours": 232.78,
        "R2_score": -0.8280,
        "Baseline_Improvement": "-7.2%",
        "Leakage_Status": "LEAKAGE_SAFE"
    },
    {
        "Model": "XGBoost Regressor (Random Split)",
        "Task": "Regression",
        "Validation_Method": "Random Split (80/20)",
        "MAE_hours": 36.70,
        "RMSE_hours": 53.91,
        "R2_score": 0.9425,
        "Baseline_Improvement": "DECEPTIVE (+81.2%)",
        "Leakage_Status": "SEVERE_AUTOCORRELATION_LEAKAGE"
    },
    {
        "Model": "HistGradBoosting (Walk-Forward)",
        "Task": "Regression",
        "Validation_Method": "Walk-Forward (3-Fold)",
        "MAE_hours": 295.37,
        "RMSE_hours": 351.45,
        "R2_score": -3.9880,
        "Baseline_Improvement": "-51.6% (Fails Baseline)",
        "Leakage_Status": "LEAKAGE_SAFE"
    },
    {
        "Model": "XGBoost Regressor (Walk-Forward)",
        "Task": "Regression",
        "Validation_Method": "Walk-Forward (3-Fold)",
        "MAE_hours": 295.47,
        "RMSE_hours": 353.48,
        "R2_score": -4.0090,
        "Baseline_Improvement": "-51.7% (Fails Baseline)",
        "Leakage_Status": "LEAKAGE_SAFE"
    },
    {
        "Model": "XGBoost Risk Classifier",
        "Task": "Multi-Class Classification",
        "Validation_Method": "Walk-Forward (3-Fold)",
        "MAE_hours": "N/A (Accuracy: 32.81%)",
        "RMSE_hours": "N/A (Bal Acc: 25.03%)",
        "R2_score": "N/A (Macro F1: 0.1790)",
        "Baseline_Improvement": "N/A (ROC-AUC: 0.5351)",
        "Leakage_Status": "LEAKAGE_SAFE"
    }
]

df_res = pd.DataFrame(summary_table)
print("\nCONSOLIDATED VALIDATION TABLE:")
print(df_res.to_string(index=False))

# Export consolidated artifact
export_path = MODELS_DIR / "water_pump_consolidated_comparison.json"
with open(export_path, "w") as f:
    json.dump({"consolidated_comparison": summary_table}, f, indent=2)

print(f"\nConsolidated comparison artifact saved to: {export_path}")
print("\n" + "=" * 70)
print("PHASE 8E CONSOLIDATED COMPARISON COMPLETE")
print("=" * 70)

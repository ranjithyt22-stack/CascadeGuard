import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "data"

print("=" * 65)
print("CASCADEGUARD PHASE 7B: MULTI-ASSET MODEL VERIFICATION & REGISTRY")
print("=" * 65)

verification_results = {
    "transformer": {"model_load": False, "prediction": False},
    "chiller": {"model_load": False, "prediction": False},
    "water_pump": {"model_load": False, "prediction": False}
}

# 1. VERIFY TRANSFORMER MODEL
print("\n[1] Verifying Power Transformer Operational Model...")
tx_model_path = MODELS_DIR / "operational_stress_xgboost_v3.pkl"
tx_features_path = MODELS_DIR / "operational_features_v3.csv"
tx_data_path = DATA_DIR / "processed" / "transformer_merged.csv"

try:
    tx_model = joblib.load(tx_model_path)
    with open(tx_features_path) as f:
        tx_features = [l.strip() for l in f if l.strip()]
    verification_results["transformer"]["model_load"] = True
    print("  - Transformer model & feature list loaded: PASS")

    tx_df = pd.read_csv(tx_data_path)
    tx_sample = tx_df.iloc[0]
    tx_vals = [float(tx_sample.get(feat, 0.0)) for feat in tx_features]
    tx_X = pd.DataFrame([tx_vals], columns=tx_features)
    tx_prob = float(tx_model.predict_proba(tx_X)[0][1])
    tx_risk = round(tx_prob * 100.0, 2)
    verification_results["transformer"]["prediction"] = True
    print(f"  - Real sample inference test: PASS (OpRisk={tx_risk}%)")
except Exception as e:
    print("  - Transformer verification error:", e)


# 2. VERIFY CHILLER MODEL
print("\n[2] Verifying HVAC Chiller Multi-Class Fault Model...")
chiller_model_path = MODELS_DIR / "chiller_xgboost.pkl"
chiller_features_path = MODELS_DIR / "chiller_features.csv"
chiller_mapping_path = MODELS_DIR / "chiller_label_mapping.json"
chiller_data_path = DATA_DIR / "raw" / "chiller" / "11000.xlsx"

try:
    chiller_model = joblib.load(chiller_model_path)
    with open(chiller_features_path) as f:
        chiller_features = [l.strip() for l in f if l.strip()]
    with open(chiller_mapping_path) as f:
        chiller_mapping = json.load(f)
    verification_results["chiller"]["model_load"] = True
    print("  - Chiller model, feature list & label mapping loaded: PASS")

    chiller_df = pd.read_excel(chiller_data_path, sheet_name="Sheet1")
    chiller_sample = chiller_df.iloc[0]
    chiller_vals = [float(chiller_sample.get(feat, 0.0)) for feat in chiller_features]
    chiller_X = pd.DataFrame([chiller_vals], columns=chiller_features)
    chiller_proba = chiller_model.predict_proba(chiller_X)[0]
    
    normal_idx = int(chiller_mapping["normal_class_index"])
    p_normal = float(chiller_proba[normal_idx])
    chiller_risk = round((1.0 - p_normal) * 100.0, 2)
    verification_results["chiller"]["prediction"] = True
    print(f"  - Real sample inference test: PASS (P(Normal)={p_normal*100:.2f}%, ChillerRisk={chiller_risk}%)")
except Exception as e:
    print("  - Chiller verification error:", e)


# 3. VERIFY WATER PUMP MODEL
print("\n[3] Verifying Water Pump RUL Regression Model...")
pump_model_path = MODELS_DIR / "water_pump_xgboost.pkl"
pump_features_path = MODELS_DIR / "water_pump_features.csv"
pump_metrics_path = MODELS_DIR / "water_pump_metrics.json"
pump_data_path = DATA_DIR / "raw" / "water_pump" / "rul_hrs.csv"

try:
    pump_model = joblib.load(pump_model_path)
    with open(pump_features_path) as f:
        pump_features = [l.strip() for l in f if l.strip()]
    with open(pump_metrics_path) as f:
        pump_metrics = json.load(f)
    verification_results["water_pump"]["model_load"] = True
    print("  - Water Pump model, feature list & metrics loaded: PASS")

    pump_df = pd.read_csv(pump_data_path)
    pump_sample = pump_df.iloc[0]
    pump_vals = [float(pump_sample.get(feat, 0.0)) for feat in pump_features]
    pump_X = pd.DataFrame([pump_vals], columns=pump_features)
    pred_rul = float(pump_model.predict(pump_X)[0])
    
    rul_ref_max = pump_metrics.get("rul_reference_max", 837.48)
    raw_risk = (1.0 - pred_rul / rul_ref_max) * 100.0
    pump_risk = round(float(np.clip(raw_risk, 0.0, 100.0)), 2)
    verification_results["water_pump"]["prediction"] = True
    print(f"  - Real sample inference test: PASS (Actual RUL={pump_sample['rul']}h, Pred RUL={pred_rul:.2f}h, PumpRisk={pump_risk}%)")
except Exception as e:
    print("  - Water Pump verification error:", e)


# 4. GENERATE MODEL REGISTRY JSON
print("\n[4] Exporting Multi-Asset Model Registry...")
registry_data = {
    "system": "CascadeGuard AI Multi-Asset Risk Intelligence",
    "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
    "models": {
        "transformer": {
            "asset": "Power Transformer",
            "model_binary": "operational_stress_xgboost_v3.pkl",
            "task": "binary_classification_temporal",
            "status": "active_trained",
            "features_file": "operational_features_v3.csv",
            "metrics": {
                "test_roc_auc": 0.940,
                "validation_pr_auc": 0.352
            }
        },
        "chiller": {
            "asset": "HVAC Chiller",
            "model_binary": "chiller_xgboost.pkl",
            "task": "multiclass_fault_classification",
            "status": "trained",
            "features_file": "chiller_features.csv",
            "num_classes": 8,
            "metrics_file": "chiller_metrics.json"
        },
        "water_pump": {
            "asset": "Industrial Water Pump",
            "model_binary": "water_pump_xgboost.pkl",
            "task": "rul_regression",
            "status": "trained",
            "features_file": "water_pump_features.csv",
            "rul_reference_max_hrs": 837.48,
            "metrics_file": "water_pump_metrics.json"
        }
    },
    "verification_status": verification_results
}

registry_path = MODELS_DIR / "multi_asset_model_registry.json"
with open(registry_path, "w") as f:
    json.dump(registry_data, f, indent=2)

print(f"Model registry saved to: {registry_path}")

print("\n" + "=" * 65)
print("MULTI-ASSET MODEL VERIFICATION SUMMARY:")
for asset, res in verification_results.items():
    l_status = "PASS" if res["model_load"] else "FAIL"
    p_status = "PASS" if res["prediction"] else "FAIL"
    print(f"  - {asset.upper():12s} | Model Load: {l_status:4s} | Sample Inference: {p_status:4s}")
print("=" * 65)

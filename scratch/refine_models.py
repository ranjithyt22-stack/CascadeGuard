import os
import json
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, accuracy_score, f1_score
from xgboost import XGBClassifier, XGBRegressor

def refine_chiller_and_dga_models():
    # 1. Chiller Fault Model
    print("=== Refining Model 4: Chiller Fault Classifier ===")
    df_chiller = pd.read_csv("data/processed/chiller_processed.csv")
    features_chiller = ["TEI", "TEO", "TCI", "TCO", "kW", "TEA", "TCA", "TRE", "TRC", "TRC_sub", "T_suc", "Tsh_suc", "TR_dis", "Tsh_dis", "TO_sump", "PO_net"]
    target_chiller = "label"
    
    le = LabelEncoder()
    y_encoded = le.fit_transform(df_chiller[target_chiller])
    X = df_chiller[features_chiller]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded)
    
    model_chiller = XGBClassifier(n_estimators=100, max_depth=6, learning_rate=0.1, objective="multi:softprob", num_class=len(le.classes_), random_state=42)
    model_chiller.fit(X_train, y_train)
    
    preds_chiller = model_chiller.predict(X_test)
    acc = accuracy_score(y_test, preds_chiller)
    f1 = f1_score(y_test, preds_chiller, average="macro")
    print(f"Refined Model 4 (Chiller) Metrics -> Stratified Accuracy: {acc:.4f}, Macro F1: {f1:.4f}")
    
    joblib.dump(model_chiller, "models/production/model_4_chiller_fault.pkl")
    joblib.dump(le, "models/production/chiller_label_encoder.pkl")
    with open("models/production/model_4_chiller_fault_meta.json", "w") as f:
        json.dump({"model_id": "Model-4-ChillerFault", "algorithm": "XGBClassifier", "metrics": {"accuracy": round(acc, 4), "macro_f1": round(f1, 4)}}, f, indent=2)

    # 2. DGA Health Model
    print("=== Refining Model 3: Transformer Health Index Model ===")
    df_dga = pd.read_csv("data/processed/transformer_health_processed.csv")
    features_dga = ["Hydrogen", "Oxigen", "Nitrogen", "Methane", "CO", "CO2", "Ethylene", "Ethane", "Acethylene", "DBDS", "Power factor", "Interfacial V", "Dielectric rigidity", "Water content"]
    target_dga = "Health index"
    
    X_dga = df_dga[features_dga]
    y_dga = df_dga[target_dga]
    
    X_train, X_test, y_train, y_test = train_test_split(X_dga, y_dga, test_size=0.2, random_state=42)
    model_dga = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42)
    model_dga.fit(X_train, y_train)
    
    preds_dga = model_dga.predict(X_test)
    mae = mean_absolute_error(y_test, preds_dga)
    r2 = r2_score(y_test, preds_dga)
    print(f"Refined Model 3 (DGA Health) Metrics -> MAE: {mae:.2f} pts, R2: {r2:.4f}")
    
    joblib.dump(model_dga, "models/production/model_3_transformer_health.pkl")
    with open("models/production/model_3_transformer_health_meta.json", "w") as f:
        json.dump({"model_id": "Model-3-TransformerHealth", "algorithm": "RandomForestRegressor", "metrics": {"mae": round(mae, 2), "r2": round(r2, 4)}}, f, indent=2)

if __name__ == "__main__":
    refine_chiller_and_dga_models()

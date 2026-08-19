import os
import json
import joblib
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, accuracy_score, precision_score, recall_score, f1_score
from xgboost import XGBClassifier, XGBRegressor

def train_model_1_hospital_load():
    print("=== Training MODEL 1: Hospital Electrical Load Forecaster ===")
    df = pd.read_csv("data/processed/hospital_load_processed.csv")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    
    df["load_lag1"] = df["total_load_kw"].shift(1)
    df["load_lag6"] = df["total_load_kw"].shift(6)
    df["load_lag24"] = df["total_load_kw"].shift(24)
    df["temp_lag1"] = df["ambient_temp"].shift(1)
    
    df.dropna(inplace=True)
    
    split_idx = int(len(df) * 0.8)
    train = df.iloc[:split_idx]
    test = df.iloc[split_idx:]
    
    features = ["ambient_temp", "hour", "day_of_week", "load_lag1", "load_lag6", "load_lag24", "temp_lag1"]
    target = "total_load_kw"
    
    X_train, y_train = train[features], train[target]
    X_test, y_test = test[features], test[target]
    
    model = XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.05, random_state=42)
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    r2 = r2_score(y_test, preds)
    
    print(f"Model 1 (Hospital Load) Metrics -> MAE: {mae:.2f} kW, RMSE: {rmse:.2f} kW, R2: {r2:.4f}")
    
    os.makedirs("models/production", exist_ok=True)
    joblib.dump(model, "models/production/model_1_hospital_load.pkl")
    
    metadata = {
        "model_id": "Model-1-HospitalLoad",
        "algorithm": "XGBRegressor",
        "features": features,
        "target": target,
        "metrics": {"mae_kw": round(mae, 2), "rmse_kw": round(rmse, 2), "r2": round(r2, 4)}
    }
    with open("models/production/model_1_hospital_load_meta.json", "w") as f:
        json.dump(metadata, f, indent=2)

def train_model_2_transformer_thermal():
    print("=== Training MODEL 2: Transformer Thermal Predictor ===")
    df = pd.read_csv("data/processed/transformer_processed.csv")
    
    df["load"] = df["active_power_kw"].fillna(50.0)
    df["current"] = df["total_current_avg"].fillna(100.0)
    df["voltage"] = df["voltage_avg"].fillna(230.0)
    df["pf"] = df["Avg_PF"].fillna(0.95)
    df["ambient_temp"] = df["ATI"].fillna(30.0)
    
    # Predict next OTI step with lag features
    df["oti_lag1"] = df["OTI"].shift(1)
    df["oti_lag5"] = df["OTI"].shift(5)
    df["wti_lag1"] = df["WTI"].shift(1)
    df["target_oti"] = df["OTI"].shift(-15) # 15m ahead prediction
    df.dropna(subset=["target_oti", "oti_lag1", "oti_lag5", "wti_lag1"], inplace=True)
    
    split_idx = int(len(df) * 0.8)
    train = df.iloc[:split_idx]
    test = df.iloc[split_idx:]
    
    features = ["load", "current", "voltage", "pf", "ambient_temp", "OTI", "WTI", "OLI", "oti_lag1", "oti_lag5", "wti_lag1"]
    target = "target_oti"
    
    X_train, y_train = train[features], train[target]
    X_test, y_test = test[features], test[target]
    
    model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    r2 = r2_score(y_test, preds)
    
    print(f"Model 2 (Transformer Thermal) Metrics -> MAE: {mae:.2f} degC, RMSE: {rmse:.2f} degC, R2: {r2:.4f}")
    
    joblib.dump(model, "models/production/model_2_transformer_thermal.pkl")
    
    metadata = {
        "model_id": "Model-2-TransformerThermal",
        "algorithm": "RandomForestRegressor",
        "features": features,
        "target": target,
        "metrics": {"mae_degc": round(mae, 2), "rmse_degc": round(rmse, 2), "r2": round(r2, 4)}
    }
    with open("models/production/model_2_transformer_thermal_meta.json", "w") as f:
        json.dump(metadata, f, indent=2)

def train_model_3_transformer_health():
    print("=== Training MODEL 3: Transformer Health Index Model ===")
    df = pd.read_csv("data/processed/transformer_health_processed.csv")
    
    features = ["Hydrogen", "Oxigen", "Nitrogen", "Methane", "CO", "CO2", "Ethylene", "Ethane", "Acethylene", "DBDS", "Power factor", "Interfacial V", "Dielectric rigidity", "Water content"]
    target = "Health index"
    
    # Standard split
    split_idx = int(len(df) * 0.8)
    train = df.iloc[:split_idx]
    test = df.iloc[split_idx:]
    
    X_train, y_train = train[features], train[target]
    X_test, y_test = test[features], test[target]
    
    model = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42)
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    r2 = r2_score(y_test, preds)
    
    print(f"Model 3 (Transformer Health) Metrics -> MAE: {mae:.2f} pts, RMSE: {rmse:.2f} pts, R2: {r2:.4f}")
    
    joblib.dump(model, "models/production/model_3_transformer_health.pkl")
    
    metadata = {
        "model_id": "Model-3-TransformerHealth",
        "algorithm": "RandomForestRegressor",
        "features": features,
        "target": target,
        "metrics": {"mae": round(mae, 2), "rmse": round(rmse, 2), "r2": round(r2, 4)}
    }
    with open("models/production/model_3_transformer_health_meta.json", "w") as f:
        json.dump(metadata, f, indent=2)

def train_model_4_chiller_performance():
    print("=== Training MODEL 4: Chiller Performance & Fault Model ===")
    df = pd.read_csv("data/processed/chiller_processed.csv")
    
    features = ["TEI", "TEO", "TCI", "TCO", "kW", "TEA", "TCA", "TRE", "TRC", "TRC_sub", "T_suc", "Tsh_suc", "TR_dis", "Tsh_dis", "TO_sump", "PO_net"]
    target = "label"
    
    le = LabelEncoder()
    y_encoded = le.fit_transform(df[target])
    X = df[features]
    
    split_idx = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y_encoded[:split_idx], y_encoded[split_idx:]
    
    model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    f1 = f1_score(y_test, preds, average="macro")
    
    print(f"Model 4 (Chiller Fault) Metrics -> Accuracy: {acc:.4f}, Macro F1: {f1:.4f}")
    
    joblib.dump(model, "models/production/model_4_chiller_fault.pkl")
    joblib.dump(le, "models/production/chiller_label_encoder.pkl")
    
    metadata = {
        "model_id": "Model-4-ChillerFault",
        "algorithm": "RandomForestClassifier",
        "features": features,
        "target": target,
        "metrics": {"accuracy": round(acc, 4), "macro_f1": round(f1, 4)}
    }
    with open("models/production/model_4_chiller_fault_meta.json", "w") as f:
        json.dump(metadata, f, indent=2)

def train_model_5_water_pump_rul():
    print("=== Training MODEL 5: Water Pump RUL Risk Classifier ===")
    df = pd.read_csv("data/processed/water_pump_5m_sampled.csv")
    
    sensor_cols = [c for c in df.columns if c.startswith("sensor_")]
    target = "risk_state_code"
    
    split_idx = int(len(df) * 0.8)
    X_train, X_test = df[sensor_cols].iloc[:split_idx], df[sensor_cols].iloc[split_idx:]
    y_train, y_test = df[target].iloc[:split_idx], df[target].iloc[split_idx:]
    
    model = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    f1 = f1_score(y_test, preds, average="macro")
    
    print(f"Model 5 (Water Pump Risk) Metrics -> Chronological Accuracy: {acc:.4f}, Macro F1: {f1:.4f}")
    
    joblib.dump(model, "models/production/model_5_water_pump_risk.pkl")
    
    metadata = {
        "model_id": "Model-5-WaterPumpRisk",
        "algorithm": "RandomForestClassifier",
        "features": sensor_cols,
        "target": target,
        "metrics": {"accuracy": round(acc, 4), "macro_f1": round(f1, 4)}
    }
    with open("models/production/model_5_water_pump_risk_meta.json", "w") as f:
        json.dump(metadata, f, indent=2)

def train_model_6_flood_risk():
    print("=== Training MODEL 6: Flood & Environmental Risk Model ===")
    np.random.seed(42)
    N = 2000
    rainfall_mm = np.random.exponential(scale=15.0, size=N)
    accum_rain_24h = rainfall_mm * 3.5 + np.random.normal(0, 5, N)
    surface_pressure_hpa = np.random.normal(1005, 10, N)
    
    water_level_cm = (accum_rain_24h * 1.8) - (surface_pressure_hpa - 1013) * 0.5 + np.random.normal(0, 2, N)
    water_level_cm = np.clip(water_level_cm, 0, 300)
    
    flood_risk_state = np.where(water_level_cm > 150, 2, np.where(water_level_cm > 60, 1, 0))
    
    df = pd.DataFrame({
        "rainfall_mm": rainfall_mm,
        "accum_rain_24h": accum_rain_24h,
        "surface_pressure_hpa": surface_pressure_hpa,
        "water_level_cm": water_level_cm,
        "flood_risk_state": flood_risk_state
    })
    
    features = ["rainfall_mm", "accum_rain_24h", "surface_pressure_hpa"]
    target = "flood_risk_state"
    
    X_train, X_test = df[features].iloc[:1600], df[features].iloc[1600:]
    y_train, y_test = df[target].iloc[:1600], df[target].iloc[1600:]
    
    model = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    f1 = f1_score(y_test, preds, average="macro")
    
    print(f"Model 6 (Flood Risk) Metrics -> Accuracy: {acc:.4f}, Macro F1: {f1:.4f}")
    
    joblib.dump(model, "models/production/model_6_flood_risk.pkl")
    
    metadata = {
        "model_id": "Model-6-FloodRisk",
        "algorithm": "RandomForestClassifier",
        "features": features,
        "target": target,
        "metrics": {"accuracy": round(acc, 4), "macro_f1": round(f1, 4)}
    }
    with open("models/production/model_6_flood_risk_meta.json", "w") as f:
        json.dump(metadata, f, indent=2)

if __name__ == "__main__":
    train_model_1_hospital_load()
    train_model_2_transformer_thermal()
    train_model_3_transformer_health()
    train_model_4_chiller_performance()
    train_model_5_water_pump_rul()
    train_model_6_flood_risk()
    print("=== PHASE D ALL 6 MODELS SUCCESSFULLY TRAINED & STORED ===")

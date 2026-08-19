import os
import glob
import pandas as pd
import numpy as np

def migrate_chiller_data():
    print("--- Processing Chiller Data ---")
    raw_path = "data/raw/chiller/11000.xlsx"
    df = pd.read_excel(raw_path, sheet_name="Sheet1")
    
    # Calculate derived HVAC metrics
    # Evaporator Flow assuming constant 300 GPM or computed from tonnage & kW
    df["evap_temp_diff"] = df["TEI"] - df["TEO"]
    df["cond_temp_diff"] = df["TCO"] - df["TCI"]
    
    # Estimate Cooling Tons (1 Ton = 12000 BTU/h = 3.517 kW)
    # Using kW and nominal COP of ~3.5-4.5
    df["estimated_cooling_tons"] = (df["kW"] * 3.517) / 1.2
    df["cop"] = np.where(df["kW"] > 0, (df["estimated_cooling_tons"] * 3.517) / df["kW"], 3.5)
    df["efficiency_kw_per_ton"] = np.where(df["estimated_cooling_tons"] > 0, df["kW"] / df["estimated_cooling_tons"], 0.8)
    
    out_path = "data/processed/chiller_processed.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved {df.shape} to {out_path}")

def migrate_transformer_data():
    print("--- Processing Transformer Data ---")
    # Load Overview.csv as anchor
    df_overview = pd.read_csv("data/raw/transformer/Overview.csv")
    df_cv = pd.read_csv("data/raw/transformer/CurrentVoltage.csv")
    df_pwr = pd.read_csv("data/raw/transformer/Power.csv")
    df_pf = pd.read_csv("data/raw/transformer/PowerFactor.csv")
    df_tot = pd.read_csv("data/raw/transformer/TotalPower.csv")
    
    # Clean duplicates on DeviceTimeStamp
    for df in [df_overview, df_cv, df_pwr, df_pf, df_tot]:
        df.drop_duplicates(subset=["DeviceTimeStamp"], inplace=True)
        df["DeviceTimeStamp"] = pd.to_datetime(df["DeviceTimeStamp"])
        
    # Merge sequentially
    merged = df_overview.merge(df_cv, on="DeviceTimeStamp", how="left")
    merged = merged.merge(df_pwr, on="DeviceTimeStamp", how="left")
    merged = merged.merge(df_pf, on="DeviceTimeStamp", how="left")
    merged = merged.merge(df_tot, on="DeviceTimeStamp", how="left")
    
    merged.sort_values("DeviceTimeStamp", inplace=True)
    merged.ffill(inplace=True)
    merged.bfill(inplace=True)
    
    # Calculate derived electrical & thermal features
    merged["total_current_avg"] = (merged["IL1"] + merged["IL2"] + merged["IL3"]) / 3.0
    merged["voltage_avg"] = (merged["VL1"] + merged["VL2"] + merged["VL3"]) / 3.0
    merged["apparent_power_kva"] = np.where(merged["KVA"].notnull() & (merged["KVA"] > 0), merged["KVA"], (merged["voltage_avg"] * merged["total_current_avg"] * np.sqrt(3)) / 1000.0)
    merged["active_power_kw"] = np.where(merged["KW"].notnull() & (merged["KW"] > 0), merged["KW"], merged["apparent_power_kva"] * merged["Avg_PF"].fillna(0.95))
    
    # Transformer thermal stress index
    merged["thermal_stress_index"] = (merged["OTI"] * 0.4) + (merged["WTI"] * 0.6)
    
    out_path = "data/processed/transformer_processed.csv"
    merged.to_csv(out_path, index=False)
    print(f"Saved {merged.shape} to {out_path}")
    
    # DGA Health Index dataset
    df_dga = pd.read_csv("data/raw/transformer/Health index1.csv")
    # Clean & save processed copy
    out_dga_path = "data/processed/transformer_health_processed.csv"
    df_dga.to_csv(out_dga_path, index=False)
    print(f"Saved {df_dga.shape} to {out_dga_path}")

def migrate_water_pump_data():
    print("--- Processing Water Pump Data ---")
    wp_path = "data/raw/water_pump/rul_hrs.csv"
    # Read full dataset in chunks or full if memory allows
    df = pd.read_csv(wp_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.sort_values("timestamp", inplace=True)
    
    # Create 4-state RUL risk classification target
    # NORMAL: RUL >= 240h, WATCH: 120h <= RUL < 240h, WARNING: 48h <= RUL < 120h, CRITICAL: RUL < 48h
    conditions = [
        (df["rul"] >= 240.0),
        (df["rul"] >= 120.0) & (df["rul"] < 240.0),
        (df["rul"] >= 48.0) & (df["rul"] < 120.0),
        (df["rul"] < 48.0)
    ]
    choices = ["NORMAL", "WATCH", "WARNING", "CRITICAL"]
    df["risk_state"] = np.select(conditions, choices, default="NORMAL")
    df["risk_state_code"] = np.select(conditions, [0, 1, 2, 3], default=0)
    
    # Forward fill missing sensor values
    sensor_cols = [c for c in df.columns if c.startswith("sensor_")]
    df[sensor_cols] = df[sensor_cols].ffill().bfill()
    
    out_full = "data/processed/water_pump_processed.csv"
    df.to_csv(out_full, index=False)
    print(f"Saved Full Pump Data {df.shape} to {out_full}")
    
    # Also save 5-minute downsampled version for fast API telemetry simulation
    df_5m = df.iloc[::5].copy()
    out_5m = "data/processed/water_pump_5m_sampled.csv"
    df_5m.to_csv(out_5m, index=False)
    print(f"Saved 5m Sampled Pump Data {df_5m.shape} to {out_5m}")

def create_hospital_load_dataset():
    print("--- Creating Hospital Electrical Load Dataset ---")
    tf_proc = pd.read_csv("data/processed/transformer_processed.csv")
    
    df_load = pd.DataFrame()
    df_load["timestamp"] = tf_proc["DeviceTimeStamp"]
    df_load["ambient_temp"] = tf_proc["ATI"]
    
    # Total facility load from transformer active power (scaled for KMCH hospital load e.g. 500-1500 kW)
    base_kw = tf_proc["active_power_kw"].fillna(50)
    # Map to representative hospital load profile (800 kW - 2200 kW peak)
    total_load_kw = (base_kw * 15.0) + 750.0 + (tf_proc["ATI"] * 12.0)
    
    df_load["total_load_kw"] = total_load_kw.round(2)
    # Medical Load Tiers:
    # P1 Critical (ICU, OT, Emergency, Life Support): ~30% of total
    # P2 Essential (Wards, Essential Lighting, Medical Gas): ~35% of total
    # P3 Deferrable (Laundry, Kitchen, Admin HVAC): ~20% of total
    # P4 Non-Critical (Admin, Optional Charging, Decorative): ~15% of total
    df_load["p1_critical_kw"] = (df_load["total_load_kw"] * 0.30).round(2)
    df_load["p2_essential_kw"] = (df_load["total_load_kw"] * 0.35).round(2)
    df_load["p3_deferrable_kw"] = (df_load["total_load_kw"] * 0.20).round(2)
    df_load["p4_noncritical_kw"] = (df_load["total_load_kw"] * 0.15).round(2)
    
    out_load = "data/processed/hospital_load_processed.csv"
    df_load.to_csv(out_load, index=False)
    print(f"Saved Hospital Load Data {df_load.shape} to {out_load}")

if __name__ == "__main__":
    migrate_chiller_data()
    migrate_transformer_data()
    migrate_water_pump_data()
    create_hospital_load_dataset()
    print("=== PHASE B DATA MIGRATION COMPLETE ===")

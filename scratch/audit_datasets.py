import os
import glob
import json
import pandas as pd
import numpy as np

def audit_csv(filepath):
    print(f"--- Auditing CSV: {filepath} ---")
    df = pd.read_csv(filepath)
    print(f"Shape: {df.shape}")
    print("Columns:", list(df.columns))
    print("Dtypes:\n", df.dtypes)
    print("Missing values:\n", df.isnull().sum())
    print("Duplicates:", df.duplicated().sum())
    print("Head:\n", df.head(3))
    print("Describe:\n", df.describe(include='all'))
    print("\n")
    return df

def audit_excel(filepath):
    print(f"--- Auditing Excel: {filepath} ---")
    xl = pd.ExcelFile(filepath)
    print("Sheet names:", xl.sheet_names)
    sheets_info = {}
    for sheet in xl.sheet_names:
        df = pd.read_excel(filepath, sheet_name=sheet)
        print(f"Sheet '{sheet}' Shape: {df.shape}")
        print("Columns:", list(df.columns))
        print("Head:\n", df.head(3))
        sheets_info[sheet] = df
    return sheets_info

if __name__ == "__main__":
    os.makedirs("scratch", exist_ok=True)
    
    # 1. Chiller
    chiller_path = "data/raw/chiller/11000.xlsx"
    if os.path.exists(chiller_path):
        audit_excel(chiller_path)
    
    # 2. Transformer
    tf_files = glob.glob("data/raw/transformer/*.csv")
    for f in tf_files:
        audit_csv(f)
        
    # 3. Water Pump
    wp_path = "data/raw/water_pump/rul_hrs.csv"
    if os.path.exists(wp_path):
        # Read sample or chunk first to avoid high memory usage if needed, or read full if memory allows
        df_wp = pd.read_csv(wp_path, nrows=1000)
        print(f"--- Auditing Water Pump (Sample 1000 rows): {wp_path} ---")
        print(f"Columns: {list(df_wp.columns)}")
        print(f"Head:\n{df_wp.head(3)}")
        # Get total line count / row count
        with open(wp_path, 'r', encoding='utf-8') as f:
            line_count = sum(1 for line in f) - 1
        print(f"Total Rows: {line_count}, Columns: {len(df_wp.columns)}")

import pandas as pd
import json

def inspect_chiller():
    xl = pd.ExcelFile("data/raw/chiller/11000.xlsx")
    print("CHILLER SHEETS:", xl.sheet_names)
    for sheet in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sheet)
        print(f"\n--- Sheet: {sheet} ---")
        print("Shape:", df.shape)
        print("Columns:", list(df.columns))
        print("Head:\n", df.head(2))

def inspect_transformer():
    tf_files = ["CurrentVoltage.csv", "Health index1.csv", "Overview.csv", "Power.csv", "PowerFactor.csv", "TotalPower.csv"]
    for fname in tf_files:
        path = f"data/raw/transformer/{fname}"
        df = pd.read_csv(path)
        print(f"\n--- Transformer File: {fname} ---")
        print("Shape:", df.shape)
        print("Columns:", list(df.columns))
        print("Dtypes:\n", df.dtypes)
        print("Head:\n", df.head(2))

def inspect_water_pump():
    wp_path = "data/raw/water_pump/rul_hrs.csv"
    df = pd.read_csv(wp_path, nrows=5)
    print("\n--- Water Pump File: rul_hrs.csv ---")
    print("Shape (sample 5 rows):", df.shape)
    print("Columns:", list(df.columns))
    print("Head:\n", df.head(2))

if __name__ == "__main__":
    inspect_chiller()
    inspect_transformer()
    inspect_water_pump()

import pandas as pd
from pathlib import Path

DATA_DIR = Path("data/raw")

files = list(DATA_DIR.glob("*.csv"))

print(f"Found {len(files)} CSV files\n")

for file in files:
    print("=" * 70)
    print(f"FILE: {file.name}")

    df = pd.read_csv(file)

    print("Shape:", df.shape)

    print("\nColumns:")
    for i, col in enumerate(df.columns, 1):
        print(f"{i}. {col}")

    print("\nFirst 3 rows:")
    print(df.head(3).to_string())

    print("\nMissing values:")
    print(df.isnull().sum().to_string())

    print("\n")
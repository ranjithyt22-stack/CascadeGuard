import pandas as pd
from pathlib import Path

file = Path("data/raw/Health index1.csv")

print("=" * 70)
print("HEALTH INDEX DATASET")
print("=" * 70)

df = pd.read_csv(file)

print("\nShape:")
print(df.shape)

print("\nColumns:")
for i, col in enumerate(df.columns, 1):
    print(f"{i}. {col}")

print("\nFirst 10 rows:")
print(df.head(10).to_string())

print("\nData types:")
print(df.dtypes)

print("\nMissing values:")
print(df.isnull().sum())

print("\nStatistics:")
print(df.describe(include="all").to_string())
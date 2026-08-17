import pandas as pd
from pathlib import Path

DATA_DIR = Path("data/raw")
OUTPUT_DIR = Path("data/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

files = {
    "current": DATA_DIR / "CurrentVoltage.csv",
    "overview": DATA_DIR / "Overview.csv",
    "power": DATA_DIR / "Power.csv",
    "pf": DATA_DIR / "PowerFactor.csv",
    "total": DATA_DIR / "TotalPower.csv"
}


def load_file(path):
    df = pd.read_csv(path)

    # Convert timestamp
    df["DeviceTimeStamp"] = pd.to_datetime(
        df["DeviceTimeStamp"],
        errors="coerce"
    )

    # Remove invalid timestamps
    df = df.dropna(subset=["DeviceTimeStamp"])

    # Remove duplicate timestamps
    df = df.drop_duplicates(subset=["DeviceTimeStamp"])

    # Sort
    df = df.sort_values("DeviceTimeStamp")

    return df


print("Loading datasets...\n")

current = load_file(files["current"])
overview = load_file(files["overview"])
power = load_file(files["power"])
pf = load_file(files["pf"])
total = load_file(files["total"])

print("Rows after cleaning:")
print("CurrentVoltage:", len(current))
print("Overview:", len(overview))
print("Power:", len(power))
print("PowerFactor:", len(pf))
print("TotalPower:", len(total))


# Use Overview as the base because it contains
# transformer temperature, oil level and alarm/trip information.
merged = overview.copy()


def merge_dataset(base, new_df, name):
    return pd.merge_asof(
        base.sort_values("DeviceTimeStamp"),
        new_df.sort_values("DeviceTimeStamp"),
        on="DeviceTimeStamp",
        direction="nearest",
        tolerance=pd.Timedelta("7min"),
        suffixes=("", f"_{name}")
    )


print("\nMerging CurrentVoltage...")
merged = merge_dataset(merged, current, "current")

print("Merging Power...")
merged = merge_dataset(merged, power, "power")

print("Merging PowerFactor...")
merged = merge_dataset(merged, pf, "pf")

print("Merging TotalPower...")
merged = merge_dataset(merged, total, "total")


# Sort final dataset
merged = merged.sort_values("DeviceTimeStamp")

# Save
output_file = OUTPUT_DIR / "transformer_merged.csv"
merged.to_csv(output_file, index=False)

print("\n" + "=" * 70)
print("MERGE COMPLETE")
print("=" * 70)

print("Final shape:", merged.shape)

print("\nColumns:")
for i, col in enumerate(merged.columns, 1):
    print(f"{i}. {col}")

print("\nMissing values:")
print(merged.isnull().sum())

print("\nAlarm / Trip distribution:")
for col in ["OTI_A", "OTI_T", "MOG_A"]:
    if col in merged.columns:
        print(f"\n{col}:")
        print(merged[col].value_counts(dropna=False))

print("\nSaved to:")
print(output_file)
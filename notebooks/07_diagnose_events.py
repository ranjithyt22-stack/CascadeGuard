import pandas as pd

df = pd.read_csv("data/processed/transformer_merged.csv")

df["DeviceTimeStamp"] = pd.to_datetime(df["DeviceTimeStamp"])

df["thermal_event"] = (
    (df["OTI_A"] == 1) |
    (df["OTI_T"] == 1)
).astype(int)

print("=" * 70)
print("THERMAL EVENT DIAGNOSTICS")
print("=" * 70)

# --------------------------------------------------
# Overall period
# --------------------------------------------------

print("\nDataset period:")
print("Start:", df["DeviceTimeStamp"].min())
print("End  :", df["DeviceTimeStamp"].max())

# --------------------------------------------------
# Event timestamps
# --------------------------------------------------

events = df[df["thermal_event"] == 1].copy()

print("\nTotal thermal events:", len(events))

print("\nFirst 20 events:")
print(
    events[
        ["DeviceTimeStamp", "OTI", "WTI", "ATI", "OLI", "OTI_A", "OTI_T"]
    ].head(20).to_string(index=False)
)

# --------------------------------------------------
# Events by month
# --------------------------------------------------

events["Month"] = events["DeviceTimeStamp"].dt.to_period("M")

print("\nEvents by month:")
print(events["Month"].value_counts().sort_index())

# --------------------------------------------------
# Events by date
# --------------------------------------------------

events["Date"] = events["DeviceTimeStamp"].dt.date

print("\nEvents by date:")
print(events["Date"].value_counts().sort_index().to_string())

# --------------------------------------------------
# Last event
# --------------------------------------------------

if len(events) > 0:

    print("\nFirst event:")
    print(events["DeviceTimeStamp"].min())

    print("\nLast event:")
    print(events["DeviceTimeStamp"].max())

# --------------------------------------------------
# Target distribution by chronological 80/20 split
# --------------------------------------------------

split = int(len(df) * 0.80)

train = df.iloc[:split]
test = df.iloc[split:]

print("\n" + "=" * 70)
print("CHRONOLOGICAL SPLIT")
print("=" * 70)

print("\nTraining period:")
print(train["DeviceTimeStamp"].min(), "to", train["DeviceTimeStamp"].max())

print("Training thermal events:", train["thermal_event"].sum())

print("\nTesting period:")
print(test["DeviceTimeStamp"].min(), "to", test["DeviceTimeStamp"].max())

print("Testing thermal events:", test["thermal_event"].sum())
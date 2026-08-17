import pandas as pd
import numpy as np
from pathlib import Path

from xgboost import XGBClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    average_precision_score
)
import joblib


# ============================================================
# 1. Load merged monitoring dataset
# ============================================================

file = Path("data/processed/transformer_merged.csv")

df = pd.read_csv(file)

df["DeviceTimeStamp"] = pd.to_datetime(
    df["DeviceTimeStamp"],
    errors="coerce"
)

df = df.sort_values("DeviceTimeStamp").reset_index(drop=True)

print("=" * 70)
print("CASCADEGUARD - OPERATIONAL STRESS MODEL")
print("=" * 70)

print("Dataset:", df.shape)


# ============================================================
# 2. Create thermal event
# ============================================================

# A thermal event is:
# OTI alarm OR OTI trip

df["thermal_event"] = (
    (df["OTI_A"] == 1) |
    (df["OTI_T"] == 1)
).astype(int)

print("\nCurrent thermal events:")
print(df["thermal_event"].value_counts())


# ============================================================
# 3. Create FUTURE 60-MINUTE target
# ============================================================

timestamps = df["DeviceTimeStamp"].values
events = df["thermal_event"].values

future_event = np.zeros(len(df), dtype=int)

for i in range(len(df)):

    current_time = timestamps[i]

    # Look up to 60 minutes into the future
    end_time = current_time + np.timedelta64(60, "m")

    # Find first timestamp beyond the 60-minute window
    right = np.searchsorted(
        timestamps,
        end_time,
        side="right"
    )

    # Exclude current row
    if right > i + 1:

        if events[i + 1:right].max() == 1:
            future_event[i] = 1


df["future_thermal_event_60m"] = future_event


print("\nFuture 60-minute target:")
print(
    df["future_thermal_event_60m"].value_counts()
)


# ============================================================
# 4. Select operational features
# ============================================================

features = [
    # Temperature
    "ATI",
    "OTI",
    "WTI",

    # Oil
    "OLI",

    # Voltage
    "VL1",
    "VL2",
    "VL3",
    "VL12",
    "VL23",
    "VL31",

    # Current
    "IL1",
    "IL2",
    "IL3",
    "INUT",

    # Power
    "WL1",
    "WL2",
    "WL3",
    "VAL1",
    "VAL2",
    "VAL3",
    "RVAL1",
    "RVAL2",
    "RVAL3",

    # Power factor
    "PFL1",
    "PFL2",
    "PFL3",
    "Avg_PF",
    "Sum_PF",

    # Frequency / distortion
    "FRQ",
    "THDVL1",
    "THDVL2",
    "THDVL3",
    "THDIL1",
    "THDIL2",
    "THDIL3",

    # Total power
    "KW",
    "KVA",
    "KVAR",
    "MPD",
    "MKVAD"
]


# ============================================================
# 5. Remove rows with missing sensor values
# ============================================================

df_model = df.dropna(
    subset=features + ["future_thermal_event_60m"]
).copy()

print("\nRows after removing missing values:")
print(len(df_model))


# ============================================================
# 6. Chronological train/test split
# ============================================================

# IMPORTANT:
# We use time-based split rather than random split
# because this is a future prediction problem.

split_index = int(len(df_model) * 0.80)

train = df_model.iloc[:split_index]
test = df_model.iloc[split_index:]


X_train = train[features]
y_train = train["future_thermal_event_60m"]

X_test = test[features]
y_test = test["future_thermal_event_60m"]


print("\nTraining samples:", len(train))
print("Testing samples:", len(test))

print("\nTraining target:")
print(y_train.value_counts())

print("\nTesting target:")
print(y_test.value_counts())


# ============================================================
# 7. Handle class imbalance
# ============================================================

positive = y_train.sum()
negative = len(y_train) - positive

if positive > 0:
    scale_pos_weight = negative / positive
else:
    scale_pos_weight = 1

print("\nScale positive weight:", scale_pos_weight)


# ============================================================
# 8. Train XGBoost classifier
# ============================================================

model = XGBClassifier(
    n_estimators=300,
    max_depth=4,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=scale_pos_weight,
    objective="binary:logistic",
    eval_metric="logloss",
    random_state=42
)

print("\nTraining operational XGBoost...")

model.fit(
    X_train,
    y_train
)


# ============================================================
# 9. Predictions
# ============================================================

probabilities = model.predict_proba(X_test)[:, 1]

predictions = (
    probabilities >= 0.50
).astype(int)


# ============================================================
# 10. Evaluation
# ============================================================

print("\n" + "=" * 70)
print("OPERATIONAL MODEL PERFORMANCE")
print("=" * 70)

print("\nClassification Report:")

print(
    classification_report(
        y_test,
        predictions,
        zero_division=0
    )
)

print("\nConfusion Matrix:")

print(
    confusion_matrix(
        y_test,
        predictions
    )
)

# ROC-AUC only works when test contains both classes
if len(np.unique(y_test)) == 2:

    roc_auc = roc_auc_score(
        y_test,
        probabilities
    )

    pr_auc = average_precision_score(
        y_test,
        probabilities
    )

    print(f"\nROC-AUC: {roc_auc:.3f}")
    print(f"PR-AUC : {pr_auc:.3f}")


# ============================================================
# 11. Feature importance
# ============================================================

importance = pd.DataFrame({
    "Feature": features,
    "Importance": model.feature_importances_
})

importance = importance.sort_values(
    "Importance",
    ascending=False
)

print("\nTop Operational Risk Factors:")

print(
    importance.head(15).to_string(index=False)
)


# ============================================================
# 12. Save model
# ============================================================

Path("models").mkdir(exist_ok=True)

joblib.dump(
    model,
    "models/operational_stress_xgboost.pkl"
)

pd.Series(features).to_csv(
    "models/operational_features.csv",
    index=False,
    header=False
)

print("\nModel saved:")
print("models/operational_stress_xgboost.pkl")

print("\nFeature list saved:")
print("models/operational_features.csv")
import pandas as pd
import numpy as np
import joblib

from pathlib import Path

from xgboost import XGBClassifier

from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score
)


# ============================================================
# 1. Load data
# ============================================================

df = pd.read_csv(
    "data/processed/transformer_merged.csv"
)

df["DeviceTimeStamp"] = pd.to_datetime(
    df["DeviceTimeStamp"]
)

df = df.sort_values(
    "DeviceTimeStamp"
).reset_index(drop=True)


# ============================================================
# 2. Thermal event
# ============================================================

df["thermal_event"] = (
    (df["OTI_A"] == 1) |
    (df["OTI_T"] == 1)
).astype(int)


# ============================================================
# 3. Future 60-minute event
# ============================================================

timestamps = df["DeviceTimeStamp"].values
events = df["thermal_event"].values

future_event = np.zeros(
    len(df),
    dtype=int
)

for i in range(len(df)):

    current_time = timestamps[i]

    end_time = (
        current_time +
        np.timedelta64(60, "m")
    )

    right = np.searchsorted(
        timestamps,
        end_time,
        side="right"
    )

    if right > i + 1:

        if events[i + 1:right].max() == 1:
            future_event[i] = 1


df["future_thermal_event"] = future_event


# ============================================================
# 4. Features
# ============================================================

features = [
    "ATI",
    "OTI",
    "WTI",
    "OLI",

    "VL1",
    "VL2",
    "VL3",
    "VL12",
    "VL23",
    "VL31",

    "IL1",
    "IL2",
    "IL3",
    "INUT",

    "WL1",
    "WL2",
    "WL3",

    "VAL1",
    "VAL2",
    "VAL3",

    "RVAL1",
    "RVAL2",
    "RVAL3",

    "PFL1",
    "PFL2",
    "PFL3",

    "Avg_PF",
    "Sum_PF",

    "FRQ",

    "THDVL1",
    "THDVL2",
    "THDVL3",

    "THDIL1",
    "THDIL2",
    "THDIL3",

    "KW",
    "KVA",
    "KVAR",

    "MPD",
    "MKVAD"
]


df = df.dropna(
    subset=features + ["future_thermal_event"]
).copy()


X = df[features]
y = df["future_thermal_event"]

# IMPORTANT:
# Measurements from the same calendar day must stay
# in the same train/test group.
groups = df["DeviceTimeStamp"].dt.date


print("=" * 70)
print("CASCADEGUARD - OPERATIONAL MODEL V2")
print("=" * 70)

print("\nDataset:", X.shape)

print("\nTarget:")
print(y.value_counts())

print("\nPositive rate:")
print(f"{y.mean() * 100:.2f}%")


# ============================================================
# 5. Stratified Group Cross Validation
# ============================================================

cv = StratifiedGroupKFold(
    n_splits=5,
    shuffle=True,
    random_state=42
)

roc_scores = []
pr_scores = []
precision_scores = []
recall_scores = []
f1_scores = []

fold = 1

for train_idx, test_idx in cv.split(
    X,
    y,
    groups
):

    print("\n" + "=" * 70)
    print(f"FOLD {fold}")
    print("=" * 70)

    X_train = X.iloc[train_idx]
    X_test = X.iloc[test_idx]

    y_train = y.iloc[train_idx]
    y_test = y.iloc[test_idx]

    print(
        "Train positives:",
        y_train.sum()
    )

    print(
        "Test positives:",
        y_test.sum()
    )

    # ----------------------------------------
    # Class imbalance
    # ----------------------------------------

    positive = y_train.sum()
    negative = len(y_train) - positive

    if positive > 0:
        weight = negative / positive
    else:
        weight = 1

    # ----------------------------------------
    # Model
    # ----------------------------------------

    model = XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,

        scale_pos_weight=weight,

        objective="binary:logistic",
        eval_metric="logloss",

        random_state=42
    )

    model.fit(
        X_train,
        y_train
    )

    probabilities = model.predict_proba(
        X_test
    )[:, 1]

    predictions = (
        probabilities >= 0.50
    ).astype(int)

    # ----------------------------------------
    # Metrics
    # ----------------------------------------

    precision = precision_score(
        y_test,
        predictions,
        zero_division=0
    )

    recall = recall_score(
        y_test,
        predictions,
        zero_division=0
    )

    f1 = f1_score(
        y_test,
        predictions,
        zero_division=0
    )

    print(
        f"Precision: {precision:.3f}"
    )

    print(
        f"Recall:    {recall:.3f}"
    )

    print(
        f"F1:        {f1:.3f}"
    )

    if len(np.unique(y_test)) == 2:

        roc = roc_auc_score(
            y_test,
            probabilities
        )

        pr = average_precision_score(
            y_test,
            probabilities
        )

        print(
            f"ROC-AUC:   {roc:.3f}"
        )

        print(
            f"PR-AUC:    {pr:.3f}"
        )

        roc_scores.append(roc)
        pr_scores.append(pr)

    precision_scores.append(precision)
    recall_scores.append(recall)
    f1_scores.append(f1)

    fold += 1


# ============================================================
# 6. Overall CV results
# ============================================================

print("\n" + "=" * 70)
print("CROSS-VALIDATION RESULTS")
print("=" * 70)

print(
    f"Mean Precision: {np.mean(precision_scores):.3f}"
)

print(
    f"Mean Recall:    {np.mean(recall_scores):.3f}"
)

print(
    f"Mean F1:        {np.mean(f1_scores):.3f}"
)

if roc_scores:

    print(
        f"Mean ROC-AUC:   {np.mean(roc_scores):.3f}"
    )

    print(
        f"Mean PR-AUC:    {np.mean(pr_scores):.3f}"
    )


# ============================================================
# 7. Train final model on all data
# ============================================================

positive = y.sum()
negative = len(y) - positive

weight = (
    negative / positive
    if positive > 0
    else 1
)

final_model = XGBClassifier(
    n_estimators=300,
    max_depth=4,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=weight,
    objective="binary:logistic",
    eval_metric="logloss",
    random_state=42
)

final_model.fit(
    X,
    y
)


# ============================================================
# 8. Feature importance
# ============================================================

importance = pd.DataFrame({
    "Feature": features,
    "Importance": final_model.feature_importances_
})

importance = importance.sort_values(
    "Importance",
    ascending=False
)

print("\n" + "=" * 70)
print("TOP OPERATIONAL RISK FACTORS")
print("=" * 70)

print(
    importance.head(15).to_string(
        index=False
    )
)


# ============================================================
# 9. Save
# ============================================================

Path("models").mkdir(
    exist_ok=True
)

joblib.dump(
    final_model,
    "models/operational_stress_xgboost_v2.pkl"
)

importance.to_csv(
    "models/operational_importance.csv",
    index=False
)

print("\nFinal model saved:")
print(
    "models/operational_stress_xgboost_v2.pkl"
)
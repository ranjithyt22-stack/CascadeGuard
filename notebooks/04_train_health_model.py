import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor
import joblib

# --------------------------------------------------
# 1. Load dataset
# --------------------------------------------------

file = Path("data/raw/Health index1.csv")

df = pd.read_csv(file)

print("=" * 70)
print("CASCADEGUARD - HEALTH INDEX MODEL")
print("=" * 70)

print("Dataset shape:", df.shape)


# --------------------------------------------------
# 2. Define features and target
# --------------------------------------------------

features = [
    "Hydrogen",
    "Oxigen",
    "Nitrogen",
    "Methane",
    "CO",
    "CO2",
    "Ethylene",
    "Ethane",
    "Acethylene",
    "DBDS",
    "Power factor",
    "Interfacial V",
    "Dielectric rigidity",
    "Water content"
]

target = "Health index"

X = df[features]
y = df[target]


print("\nFeatures:")
for feature in features:
    print("-", feature)

print("\nTarget:", target)


# --------------------------------------------------
# 3. Train / test split
# --------------------------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42
)

print("\nTraining samples:", len(X_train))
print("Testing samples:", len(X_test))


# --------------------------------------------------
# 4. XGBoost model
# --------------------------------------------------

model = XGBRegressor(
    n_estimators=300,
    max_depth=4,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    objective="reg:squarederror",
    random_state=42
)

print("\nTraining XGBoost...")

model.fit(X_train, y_train)


# --------------------------------------------------
# 5. Predictions
# --------------------------------------------------

y_pred = model.predict(X_test)

y_pred = np.clip(y_pred, 0, 100)


# --------------------------------------------------
# 6. Evaluation
# --------------------------------------------------

mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)

print("\n" + "=" * 70)
print("MODEL PERFORMANCE")
print("=" * 70)

print(f"MAE  : {mae:.2f}")
print(f"RMSE : {rmse:.2f}")
print(f"R²   : {r2:.3f}")


# --------------------------------------------------
# 7. Feature importance
# --------------------------------------------------

importance = pd.DataFrame({
    "Feature": features,
    "Importance": model.feature_importances_
})

importance = importance.sort_values(
    "Importance",
    ascending=False
)

print("\nFeature Importance:")
print(importance.to_string(index=False))


# --------------------------------------------------
# 8. Save model
# --------------------------------------------------

Path("models").mkdir(exist_ok=True)

joblib.dump(
    model,
    "models/health_index_xgboost.pkl"
)

print("\nModel saved:")
print("models/health_index_xgboost.pkl")


# --------------------------------------------------
# 9. Save feature list
# --------------------------------------------------

pd.Series(features).to_csv(
    "models/health_features.csv",
    index=False,
    header=False
)

print("Feature list saved.")
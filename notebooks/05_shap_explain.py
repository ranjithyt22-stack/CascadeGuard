import pandas as pd
import joblib
import shap
import matplotlib.pyplot as plt

# -----------------------------------------
# Load data
# -----------------------------------------

df = pd.read_csv("data/raw/Health index1.csv")

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

X = df[features]

# -----------------------------------------
# Load trained model
# -----------------------------------------

model = joblib.load("models/health_index_xgboost.pkl")

print("Model loaded successfully.")

# -----------------------------------------
# SHAP
# -----------------------------------------

explainer = shap.TreeExplainer(model)

shap_values = explainer(X)

# -----------------------------------------
# Feature importance
# -----------------------------------------

print("\nSHAP Feature Importance:")

importance = pd.DataFrame({
    "Feature": features,
    "Mean_ABS_SHAP": abs(shap_values.values).mean(axis=0)
})

importance = importance.sort_values(
    "Mean_ABS_SHAP",
    ascending=False
)

print(importance.to_string(index=False))

# -----------------------------------------
# Save importance
# -----------------------------------------

importance.to_csv(
    "models/shap_importance.csv",
    index=False
)

# -----------------------------------------
# SHAP summary plot
# -----------------------------------------

plt.figure()

shap.summary_plot(
    shap_values,
    X,
    show=False
)

plt.tight_layout()

plt.savefig(
    "models/shap_summary.png",
    dpi=200,
    bbox_inches="tight"
)

plt.close()

print("\nSHAP summary saved:")
print("models/shap_summary.png")
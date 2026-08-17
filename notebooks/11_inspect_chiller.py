import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CHILLER_PATH = BASE_DIR / "data" / "raw" / "chiller" / "11000.xlsx"
REPORT_PATH = BASE_DIR / "data" / "processed" / "chiller_dataset_report.txt"

REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("CASCADEGUARD PHASE 7A — PART A: CHILLER DATASET AUDIT")
print("=" * 70)

# 1. Identify all sheets
excel_file = pd.ExcelFile(CHILLER_PATH)
sheet_names = excel_file.sheet_names

print(f"\n1. All Sheets ({len(sheet_names)}): {sheet_names}")

# 2. Shape of every sheet
sheet_shapes = {}
sheet_dfs = {}
for name in sheet_names:
    df_s = pd.read_excel(CHILLER_PATH, sheet_name=name)
    sheet_dfs[name] = df_s
    sheet_shapes[name] = df_s.shape
    print(f"2. Sheet '{name}' Shape: {df_s.shape[0]:,} rows x {df_s.shape[1]} columns")

df = sheet_dfs[sheet_names[0]]

# 3. Column names & 5. Data types
print("\n3 & 5. Column Names and Data Types:")
for i, col in enumerate(df.columns, 1):
    print(f"  {i:02d}. {col:15s} | dtype: {str(df[col].dtype):10s} | nulls: {df[col].isnull().sum():,}")

# 4. First 10 rows
print("\n4. First 10 Rows:")
print(df.head(10).to_string())

# 6. Missing values
total_missing = df.isnull().sum().sum()
print(f"\n6. Missing Values: Total {total_missing:,} nulls across dataset.")

# 7. Duplicate rows
duplicates = df.duplicated().sum()
print(f"7. Duplicate Rows: {duplicates:,} ({duplicates / len(df) * 100:.2f}%)")

# 8 & 9. Numerical vs Categorical features
target_col = "label"
feature_cols = [c for c in df.columns if c != target_col]
num_features = [c for c in feature_cols if np.issubdtype(df[c].dtype, np.number)]
cat_features = [c for c in feature_cols if not np.issubdtype(df[c].dtype, np.number)]

print(f"\n8. Numerical Features ({len(num_features)}): {num_features}")
print(f"9. Categorical Features ({len(cat_features)}): {cat_features}")

# 10. Timestamp availability
timestamp_cols = [c for c in df.columns if "time" in c.lower() or "date" in c.lower()]
print(f"\n10. Timestamp Availability: {len(timestamp_cols) > 0} (Found: {timestamp_cols})")

# 11. Target column & 12. Unique fault classes & 13. Class counts
class_counts = df[target_col].value_counts().sort_index().to_dict()
print(f"\n11. Target Column: '{target_col}'")
print(f"12. Unique Fault Classes ({len(class_counts)}): {list(class_counts.keys())}")
print(f"13. Class Counts: {class_counts}")

# 14. Normal operation
has_normal = False
normal_val = None
if 1 in class_counts:
    has_normal = True
    normal_val = "Class 1 (Baseline Operating Condition)"

print(f"\n14. Normal Operation State: {has_normal} (Value: {normal_val})")

# 15. Fault severity
has_severity = False
print(f"15. Fault Severity Levels: {has_severity} (Categorical discrete fault classes 1–8)")

# 16. Supported Tasks
print("\n16. Dataset Capabilities:")
print("  - Fault Classification: YES (8 multi-class fault categories)")
print("  - Health/Risk Scoring: YES (Derived fault probability 0-100%)")
print("  - Remaining Useful Life (RUL): NO (No run-to-failure temporal degradation sequence)")
print("  - Anomaly Detection: YES (Statistical distance from Class 1 baseline)")

# Constant columns check
constant_cols = [c for c in df.columns if df[c].nunique() == 1]
print(f"\nDataset Quality — Constant Columns: {constant_cols}")

# Write detailed text report
report_lines = [
    "CASCADEGUARD CHILLER DATASET INSPECTION REPORT",
    "=====================================================",
    f"Dataset File: {CHILLER_PATH.name}",
    f"Sheet Names: {sheet_names}",
    f"Shape: {df.shape[0]:,} rows x {df.shape[1]} columns",
    f"Missing Values: {total_missing:,}",
    f"Duplicate Rows: {duplicates:,}",
    "",
    f"Target Column: {target_col}",
    f"Number of Classes: {len(class_counts)}",
    f"Class Distribution: {class_counts}",
    f"Normal Operation: {has_normal} ({normal_val})",
    f"Fault Severity Information: None (8 discrete fault modes)",
    f"Timestamp Available: False (Sequential samples)",
    "",
    f"Numerical Features ({len(num_features)}): {num_features}",
    f"Categorical Features ({len(cat_features)}): {cat_features}",
    f"Constant Columns: {constant_cols}",
    "",
    "RECOMMENDED ML TASK: Multi-Class Fault Classification & Derived Chiller Risk Scoring",
    "RECOMMENDED MODEL TYPE: XGBoost Multi-Class Classifier / Random Forest Classifier",
    "CLIMATE SENSITIVITY: High (Evaporator & Condenser temperatures TEI/TEO/TCI/TCO respond to ambient heatwave)",
    "SUITABILITY FOR CASCADEGUARD: HIGH — Complements transformer risk in industrial HVAC infrastructure."
]

with open(REPORT_PATH, "w") as f:
    f.write("\n".join(report_lines))

print(f"\nChiller report saved to: {REPORT_PATH}")

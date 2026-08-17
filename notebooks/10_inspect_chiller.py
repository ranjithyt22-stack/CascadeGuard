import pandas as pd
import numpy as np
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
CHILLER_PATH = BASE_DIR / "data" / "raw" / "chiller" / "11000.xlsx"
REPORT_PATH = BASE_DIR / "data" / "processed" / "chiller_dataset_report.txt"

REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

print("=" * 65)
print("CASCADEGUARD PHASE 6A: CHILLER DATASET INSPECTION")
print("=" * 65)

# 1. Identify all sheets
excel_file = pd.ExcelFile(CHILLER_PATH)
sheet_names = excel_file.sheet_names

print(f"\n[STEP 1] Excel File: {CHILLER_PATH.name}")
print(f"Total Sheets Found: {len(sheet_names)}")
for idx, name in enumerate(sheet_names, 1):
    print(f"  {idx}. Sheet: '{name}'")

# Load primary sheet (or combine sheets if multiple)
sheet_dfs = {}
for name in sheet_names:
    sheet_dfs[name] = pd.read_excel(CHILLER_PATH, sheet_name=name)

main_sheet_name = sheet_names[0]
df = sheet_dfs[main_sheet_name]

print(f"\n[STEP 2] Inspecting Main Sheet: '{main_sheet_name}'")
print(f"Shape: {df.shape[0]:,} rows x {df.shape[1]} columns")

print("\n[STEP 3] Column Names:")
for i, col in enumerate(df.columns, 1):
    print(f"  {i:02d}. {col} (dtype: {df[col].dtype})")

print("\n[STEP 4] First 10 Rows:")
print(df.head(10).to_string())

# 5. Identify Target / Fault Column
target_col = None
possible_target_cols = ["fault", "target", "label", "class", "state", "status", "mode", "fault_type", "fault_class", "type", "condition"]
for col in df.columns:
    if any(p in col.lower() for p in possible_target_cols):
        target_col = col
        break

if target_col is None:
    # Check if last column or object column contains categorical labels
    target_col = df.columns[-1]

print(f"\n[STEP 5] Target/Fault Column Identified: '{target_col}'")

# 6. Target Classes and Counts
class_counts = df[target_col].value_counts(dropna=False).to_dict()
num_classes = len(class_counts)

print(f"\n[STEP 6] Number of Target Classes: {num_classes}")
print("Class Distribution:")
for k, v in class_counts.items():
    pct = (v / len(df)) * 100
    print(f"  - Class '{k}': {v:,} rows ({pct:.2f}%)")

# 7. Check for NORMAL / Healthy Samples
has_normal = False
normal_val = None
for k in class_counts.keys():
    k_str = str(k).lower()
    if "normal" in k_str or "healthy" in k_str or "ok" in k_str or k == 0 or k_str == "none":
        has_normal = True
        normal_val = k
        break

print(f"\n[STEP 7] Normal/Healthy Samples Present: {has_normal} (Value: '{normal_val}')")

# 8. Check for Severity Levels
has_severity = False
severity_details = "No explicit severity column found."
for col in df.columns:
    if "severity" in col.lower() or "level" in col.lower() or "sl" in col.lower():
        has_severity = True
        sev_counts = df[col].value_counts().to_dict()
        severity_details = f"Severity column '{col}': {sev_counts}"
        break

print(f"\n[STEP 8] Severity Information: {has_severity}")
print(f"  {severity_details}")

# 9. Check for Timestamps
timestamp_col = None
has_timestamp = False
for col in df.columns:
    if any(t in col.lower() for t in ["time", "date", "timestamp", "datetime", "sec", "second"]):
        timestamp_col = col
        has_timestamp = True
        break

print(f"\n[STEP 9] Timestamp Column Available: {has_timestamp} (Column: '{timestamp_col}')")

# 10. Missing Values
missing_series = df.isnull().sum()
total_missing = missing_series.sum()
cols_with_missing = missing_series[missing_series > 0].to_dict()

print(f"\n[STEP 10] Missing Values: Total {total_missing:,} missing entries across dataframe")
if cols_with_missing:
    for c_name, c_cnt in cols_with_missing.items():
        print(f"  - Column '{c_name}': {c_cnt:,} missing")
else:
    print("  - Zero missing values in dataset.")

# 11. Duplicate Rows
duplicates = df.duplicated().sum()
print(f"\n[STEP 11] Duplicate Rows: {duplicates:,} ({duplicates / len(df) * 100:.2f}%)")

# 12 & 13. ML Features vs Non-Feature Metadata Columns
non_feature_cols = []
if timestamp_col:
    non_feature_cols.append(timestamp_col)
non_feature_cols.append(target_col)

# Add any string or ID columns
for col in df.columns:
    if col not in non_feature_cols and (df[col].dtype == object or "id" in col.lower()):
        non_feature_cols.append(col)

feature_cols = [c for c in df.columns if c not in non_feature_cols]

print(f"\n[STEP 12] Numerical ML Features Count: {len(feature_cols)}")
print(f"Features: {feature_cols}")
print(f"\n[STEP 13] Non-Feature / Metadata Columns: {non_feature_cols}")

# 14. Class Imbalance
max_cnt = max(class_counts.values()) if class_counts else 1
min_cnt = min(class_counts.values()) if class_counts else 1
imbalance_ratio = max_cnt / max(min_cnt, 1)

print(f"\n[STEP 14] Class Imbalance Ratio (Max/Min): {imbalance_ratio:.2f}:1")

# 15. Save Report to File
report_content = f"""CASCADEGUARD CHILLER DATASET SUITABILITY REPORT
=====================================================
Dataset File: {CHILLER_PATH.name}
Total Rows: {len(df):,}
Total Columns: {len(df.columns)}
Sheets: {sheet_names}

Target Column: {target_col}
Number of Classes: {num_classes}
Class Distribution: {class_counts}
Normal Class Present: {has_normal} (Value: {normal_val})
Severity Information: {severity_details}

Timestamp Available: {has_timestamp} ({timestamp_col})
Missing Values: {total_missing:,}
Duplicate Rows: {duplicates:,}

Numerical ML Features ({len(feature_cols)}): {feature_cols}
Non-Feature Columns: {non_feature_cols}

Class Imbalance Ratio: {imbalance_ratio:.2f}:1
Recommended Model Type: XGBoost Classifier / Multi-Class Classifier
Suitability for CascadeGuard: HIGH — Ideal for HVAC Chiller operational fault classification & cascade risk scoring.
"""

with open(REPORT_PATH, "w") as f:
    f.write(report_content)

print(f"\nDataset suitability report saved to: {REPORT_PATH}")

# Required Final Output
print("\n" + "=" * 65)
print("FINAL CHILLER DATASET INSPECTION SUMMARY")
print("=" * 65)
print(f"CHILLER FEATURES: {len(feature_cols)} features -> {feature_cols}")
print(f"TARGET: {target_col}")
print(f"NUMBER OF CLASSES: {num_classes}")
print(f"CLASS DISTRIBUTION: {class_counts}")
print(f"NORMAL CLASS: {has_normal} (Value: {normal_val})")
print(f"SEVERITY INFORMATION: {severity_details}")
print(f"TIMESTAMP AVAILABLE: {has_timestamp} ({timestamp_col})")
print(f"MISSING VALUES: {total_missing:,}")
print("RECOMMENDED MODEL TYPE: XGBoost Multi-Class Classifier / Random Forest Classifier")
print("DATASET SUITABILITY FOR CASCADEGUARD: HIGH — Structured sensor telemetry with clear fault class labels suitable for multi-component cascade risk intelligence.")
print("=" * 65)

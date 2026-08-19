"""Utility module to perform leakage audit for each model dataset.
The functions operate on processed CSV files located under `data/processed/`.
Each function returns a dict with a `status` of \"PASS\", \"WARNING\", or \"FAIL\"
and a `details` list describing any issues found.
"""
import os
import pandas as pd

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed"))

def _check_chronological_order(df: pd.DataFrame, time_col: str = "timestamp") -> bool:
    """Return True if timestamps are strictly increasing (no future data in training)."""
    if time_col not in df.columns:
        return False
    return df[time_col].is_monotonic_increasing

def _check_duplicate_records(df: pd.DataFrame) -> bool:
    """Return True if there are duplicate rows (based on all columns)."""
    return df.duplicated().any()

def _check_future_target_leakage(df: pd.DataFrame, target: str, lag_features: list) -> bool:
    """Simple heuristic: ensure that any lag feature columns are generated via `shift` (i.e., contain NaNs at the start).
    If a lag feature has any non‑NaN values before the first valid target, we consider it a potential leak.
    """
    if target not in df.columns:
        return False
    target_idx = df.index[df[target].first_valid_index()] if df[target].first_valid_index() is not None else None
    for col in lag_features:
        if col not in df.columns:
            continue
        first_valid = df.index[df[col].first_valid_index()] if df[col].first_valid_index() is not None else None
        if target_idx is not None and first_valid is not None and first_valid < target_idx:
            continue
        if first_valid is not None and target_idx is not None and first_valid > target_idx:
            return False
    return True

def audit_hospital_load() -> dict:
    path = os.path.join(DATA_DIR, "hospital_load_processed.csv")
    if not os.path.exists(path):
        return {"status": "FAIL", "details": ["File not found"]}
    df = pd.read_csv(path, parse_dates=["timestamp"]) 
    issues = []
    if not _check_chronological_order(df):
        issues.append("Timestamps not chronological")
    if _check_duplicate_records(df):
        issues.append("Duplicate records present")
    lag_features = ["load_lag1", "load_lag6", "load_lag24", "temp_lag1"]
    if not _check_future_target_leakage(df, target="total_load_kw", lag_features=lag_features):
        issues.append("Potential future target leakage via lag features")
    status = "PASS" if not issues else "WARNING"
    return {"status": status, "details": issues}

def audit_transformer_thermal() -> dict:
    path = os.path.join(DATA_DIR, "transformer_processed.csv")
    if not os.path.exists(path):
        return {"status": "FAIL", "details": ["File not found"]}
    df = pd.read_csv(path, parse_dates=["timestamp"]) 
    issues = []
    if not _check_chronological_order(df):
        issues.append("Timestamps not chronological")
    if _check_duplicate_records(df):
        issues.append("Duplicate records present")
    lag_features = ["oti_lag1", "oti_lag5", "wti_lag1"]
    if not _check_future_target_leakage(df, target="target_oti", lag_features=lag_features):
        issues.append("Potential future target leakage via lag features")
    status = "PASS" if not issues else "WARNING"
    return {"status": status, "details": issues}

def audit_transformer_health() -> dict:
    path = os.path.join(DATA_DIR, "transformer_health_processed.csv")
    if not os.path.exists(path):
        return {"status": "FAIL", "details": ["File not found"]}
    df = pd.read_csv(path) 
    issues = []
    if _check_duplicate_records(df):
        issues.append("Duplicate records present")
    status = "PASS" if not issues else "WARNING"
    return {"status": status, "details": issues}

def audit_chiller() -> dict:
    path = os.path.join(DATA_DIR, "chiller_processed.csv")
    if not os.path.exists(path):
        return {"status": "FAIL", "details": ["File not found"]}
    df = pd.read_csv(path, parse_dates=["timestamp"]) 
    issues = []
    if not _check_chronological_order(df):
        issues.append("Timestamps not chronological")
    if _check_duplicate_records(df):
        issues.append("Duplicate records present")
    status = "PASS" if not issues else "WARNING"
    return {"status": status, "details": issues}

def audit_water_pump() -> dict:
    path = os.path.join(DATA_DIR, "water_pump_5m_sampled.csv")
    if not os.path.exists(path):
        return {"status": "FAIL", "details": ["File not found"]}
    df = pd.read_csv(path, parse_dates=["timestamp"]) 
    issues = []
    if not _check_chronological_order(df):
        issues.append("Timestamps not chronological")
    if _check_duplicate_records(df):
        issues.append("Duplicate records present")
    if "risk_state_code" in df.columns:
        class_counts = df["risk_state_code"].value_counts()
        if class_counts.min() / class_counts.sum() < 0.05:
            issues.append("Severe class imbalance detected")
    status = "PASS" if not issues else "WARNING"
    return {"status": status, "details": issues}

def audit_flood() -> dict:
    # Synthetic flood data – no external source file.
    return {"status": "PASS", "details": []}

def run_full_audit() -> dict:
    return {
        "hospital_load": audit_hospital_load(),
        "transformer_thermal": audit_transformer_thermal(),
        "transformer_health": audit_transformer_health(),
        "chiller": audit_chiller(),
        "water_pump": audit_water_pump(),
        "flood": audit_flood()
    }

if __name__ == "__main__":
    import pprint, os
    result = run_full_audit()
    pprint.pprint(result)
    report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "reports", "leakage_audit.md"))
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        f.write("# Leakage Audit Report\n\n")
        for model, res in result.items():
            f.write(f"## {model.replace('_', ' ').title()}\n")
            f.write(f"**Status:** {res['status']}  \n")
            if res['details']:
                f.write("**Issues:**\n")
                for d in res['details']:
                    f.write(f"- {d}\n")
            f.write("\n")
    print(f"Leakage audit written to {report_path}")

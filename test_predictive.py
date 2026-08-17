import requests
import sys
from pathlib import Path
import json

BASE_URL = "http://127.0.0.1:5000"
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"

print("=" * 65)
print("CASCADEGUARD PREDICTIVE FORECAST TEST SUITE (PHASE 5)")
print("=" * 65)

passed = 0
failed = 0


def log_test(name, is_pass, detail=""):
    global passed, failed
    if is_pass:
        passed += 1
        print(f"[PASS] {name} {detail}")
    else:
        failed += 1
        print(f"[FAIL] {name} - {detail}")


# 1. Model Artifact Verification
try:
    m15 = (MODELS_DIR / "predictive_15m_xgboost.pkl").exists()
    m30 = (MODELS_DIR / "predictive_30m_xgboost.pkl").exists()
    m60 = (MODELS_DIR / "predictive_60m_xgboost.pkl").exists()
    is_ok = m15 and m30 and m60
    log_test("Artifacts: Predictive XGBoost Models Exist", is_ok, f"(15m={m15}, 30m={m30}, 60m={m60})")
except Exception as e:
    log_test("Artifacts: Predictive XGBoost Models Exist", False, str(e))


# 2. Feature Schema & Threshold Config
try:
    f15 = (MODELS_DIR / "predictive_15m_features.csv").exists()
    f30 = (MODELS_DIR / "predictive_30m_features.csv").exists()
    f60 = (MODELS_DIR / "predictive_60m_features.csv").exists()
    th_file = (MODELS_DIR / "predictive_thresholds.json").exists()
    is_ok = f15 and f30 and f60 and th_file
    log_test("Artifacts: Feature Lists & Threshold Config Exist", is_ok)
except Exception as e:
    log_test("Artifacts: Feature Lists & Threshold Config Exist", False, str(e))


# 3. GET /api/predictive-forecast Endpoint Test
try:
    res = requests.get(f"{BASE_URL}/api/predictive-forecast?location=Coimbatore", timeout=15)
    data = res.json()

    pf = data.get("predictive_forecast", {})
    curr = pf.get("current", {})
    fc = pf.get("forecast", {})
    f15 = fc.get("15m", {})
    f30 = fc.get("30m", {})
    f60 = fc.get("60m", {})

    prob_ok = (
        0.0 <= f15.get("event_probability", -1) <= 1.0 and
        0.0 <= f30.get("event_probability", -1) <= 1.0 and
        0.0 <= f60.get("event_probability", -1) <= 1.0
    )

    score_ok = (
        0.0 <= curr.get("score", -1) <= 100.0 and
        0.0 <= f15.get("cascade_score", -1) <= 100.0 and
        0.0 <= f30.get("cascade_score", -1) <= 100.0 and
        0.0 <= f60.get("cascade_score", -1) <= 100.0
    )

    state_ok = (
        curr.get("level") in ["LOW", "MODERATE", "HIGH", "CRITICAL"] and
        pf.get("early_warning_state") in ["NORMAL", "WATCH", "WARNING", "CRITICAL"] and
        pf.get("trajectory") in ["RISING", "STABLE", "FALLING"]
    )

    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        prob_ok and score_ok and state_ok
    )

    log_test("GET /api/predictive-forecast", is_ok, f"(NOW={curr.get('score')}, +15m={f15.get('cascade_score')}, +30m={f30.get('cascade_score')}, +60m={f60.get('cascade_score')}, trajectory={pf.get('trajectory')})")
except Exception as e:
    log_test("GET /api/predictive-forecast", False, str(e))


# 4. GET /api/predictive-history Endpoint Test
try:
    res = requests.get(f"{BASE_URL}/api/predictive-history", timeout=10)
    data = res.json()
    history = data.get("history", [])
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        isinstance(history, list) and
        len(history) > 0 and
        "cas_60m" in history[0]
    )
    log_test("GET /api/predictive-history", is_ok, f"(stored_records={len(history)})")
except Exception as e:
    log_test("GET /api/predictive-history", False, str(e))


# 5. GET /api/live-analyze Unified Endpoint Test
try:
    res = requests.get(f"{BASE_URL}/api/live-analyze?location=Coimbatore", timeout=15)
    data = res.json()
    pf = data.get("predictive_forecast", {})
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        "predictive_forecast" in data and
        "forecast" in pf
    )
    log_test("GET /api/live-analyze (Unified Predictive Integration)", is_ok, f"(forecast_60m={pf.get('forecast', {}).get('60m', {}).get('cascade_score')})")
except Exception as e:
    log_test("GET /api/live-analyze (Unified Predictive Integration)", False, str(e))


print("=" * 65)
print(f"PREDICTIVE FORECAST SUMMARY: {passed} PASSED, {failed} FAILED")
print("=" * 65)

if failed > 0:
    sys.exit(1)

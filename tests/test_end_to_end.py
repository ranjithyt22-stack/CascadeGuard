"""
CascadeGuard AI — End-to-End Workflow & Performance Audit Test Suite
Phase 15: Final Hackathon Release Verification

Tests complete end-to-end multi-asset cascade workflows, fallback resilience,
security controls, data provenance badges, and measures actual API latencies (p50, p95, p99).
"""

import sys
import time
import requests
import numpy as np
from pathlib import Path

BASE_URL = "http://127.0.0.1:5050"
passed = 0
failed = 0


def log_test(test_name, is_success, details=""):
    global passed, failed
    if is_success:
        passed += 1
        print(f"[PASS] {test_name} {details}")
    else:
        failed += 1
        print(f"[FAIL] {test_name} {details}")


print("=" * 70)
print("CASCADEGUARD END-TO-END WORKFLOW & PERFORMANCE AUDIT TEST SUITE")
print("=================================================" * 1)


# 1. SITE REGISTRY & SELECTION
try:
    res = requests.get(f"{BASE_URL}/api/sites", timeout=10)
    data = res.json()
    is_ok = (res.status_code == 200 and data.get("success") is True and data.get("count") >= 5)
    log_test("E2E Step 1: Site Selection", is_ok, f"(sites_count={data.get('count')})")
except Exception as e:
    log_test("E2E Step 1: Site Selection", False, str(e))


# 2. LIVE CLIMATE INTELLIGENCE RETRIEVAL
try:
    res = requests.get(f"{BASE_URL}/api/climate-intelligence?location=Coimbatore", timeout=10)
    data = res.json()
    intel = data.get("intelligence") or data.get("climate_intelligence") or data.get("data", {})
    stress_val = intel.get("overall_climate_stress", intel.get("baseline_climate", {}).get("climate_stress"))
    is_ok = (res.status_code == 200 and data.get("success") is True and ("heatwave" in intel or "heatwave_analysis" in intel))
    log_test("E2E Step 2: Climate Retrieval", is_ok, f"(stress={stress_val})")
except Exception as e:
    log_test("E2E Step 2: Climate Retrieval", False, str(e))


# 3. TELEMETRY ADAPTER RETRIEVAL
try:
    res = requests.get(f"{BASE_URL}/api/telemetry/live", timeout=10)
    data = res.json()
    telem = data.get("telemetry", {})
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        "transformer" in telem and
        "chiller" in telem and
        "water_pump" in telem
    )
    log_test("E2E Step 3: Telemetry Stream Retrieval", is_ok, f"(mode={data.get('telemetry_mode')})")
except Exception as e:
    log_test("E2E Step 3: Telemetry Stream Retrieval", False, str(e))


# 4. TRANSFORMER ML INFERENCE (XGBoost V3)
try:
    res = requests.get(f"{BASE_URL}/api/live-analyze?tx_id=TX-001", timeout=10)
    data = res.json()
    is_ok = (res.status_code == 200 and data.get("success") is True and "cascade" in data)
    log_test("E2E Step 4: Transformer Inference", is_ok, f"(score={data.get('cascade', {}).get('score')})")
except Exception as e:
    log_test("E2E Step 4: Transformer Inference", False, str(e))


# 5. CHILLER ML INFERENCE (97.64% Acc XGBoost)
try:
    res = requests.get(f"{BASE_URL}/api/multi-asset-analyze", timeout=10)
    data = res.json()
    ch_asset = data.get("assets", {}).get("chiller", {})
    is_ok = (res.status_code == 200 and ("risk" in ch_asset or "chiller_risk" in ch_asset))
    log_test("E2E Step 5: Chiller Inference", is_ok, f"(chiller_risk={ch_asset.get('risk', ch_asset.get('chiller_risk'))})")
except Exception as e:
    log_test("E2E Step 5: Chiller Inference", False, str(e))


# 6. WATER PUMP DECISION SUPPORT MODEL
try:
    res = requests.get(f"{BASE_URL}/api/multi-asset-analyze", timeout=10)
    data = res.json()
    wp_asset = data.get("assets", {}).get("water_pump", {})
    wp_source = wp_asset.get("source", "") or wp_asset.get("status_label", "")
    is_ok = (res.status_code == 200 and ("DECISION" in wp_source or "SUPPORT" in wp_source or "ML_" in wp_source))
    log_test("E2E Step 6: Pump Decision Support", is_ok, f"(wp_source={wp_source})")
except Exception as e:
    log_test("E2E Step 6: Pump Decision Support", False, str(e))


# 7. MULTI-ASSET CASCADE ENGINE
try:
    res = requests.get(f"{BASE_URL}/api/multi-asset-analyze", timeout=10)
    data = res.json()
    sys_eval = data.get("system", {})
    is_ok = (res.status_code == 200 and ("system_cascade_risk" in sys_eval or "cascade_score" in sys_eval))
    log_test("E2E Step 7: Cascade Calculation", is_ok, f"(sys_risk={sys_eval.get('system_cascade_risk', sys_eval.get('cascade_score'))})")
except Exception as e:
    log_test("E2E Step 7: Cascade Calculation", False, str(e))


# 8. SHAP EXPLAINABLE AI ATTRIBUTION
try:
    res = requests.get(f"{BASE_URL}/api/live-analyze?tx_id=TX-001", timeout=10)
    data = res.json()
    is_ok = ("explainability" in data and len(data.get("explainability", {}).get("top_factors", [])) > 0)
    log_test("E2E Step 8: SHAP Explanation", is_ok, f"(factors_count={len(data.get('explainability', {}).get('top_factors', []))})")
except Exception as e:
    log_test("E2E Step 8: SHAP Explanation", False, str(e))


# 9. INCIDENT DETECTION & DEDUPLICATION ENGINE
try:
    # Trigger scenario to force incident generation
    requests.post(f"{BASE_URL}/api/telemetry/scenario", json={"scenario": "COMBINED_CASCADE"}, timeout=10)
    requests.get(f"{BASE_URL}/api/multi-asset-analyze?scenario=COMBINED_CASCADE", timeout=10)
    
    res = requests.get(f"{BASE_URL}/api/incidents", timeout=10)
    data = res.json()
    incidents = data.get("incidents") or data.get("data", {}).get("history", [])
    is_ok = (res.status_code == 200 and len(incidents) >= 1)
    log_test("E2E Step 9: Incident Detection", is_ok, f"(incidents_count={len(incidents)})")
except Exception as e:
    log_test("E2E Step 9: Incident Detection", False, str(e))


# 10. NON-CAUSAL ENGINEERING RECOMMENDATION ENGINE
try:
    res = requests.get(f"{BASE_URL}/api/incidents", timeout=10)
    data = res.json()
    incidents = data.get("incidents") or data.get("data", {}).get("history", [])
    raw_recs = incidents[0].get("recommended_actions", []) if incidents else []
    rec_count = len(raw_recs.get("actions", [])) if isinstance(raw_recs, dict) else len(raw_recs)
    is_ok = (res.status_code == 200 and rec_count >= 1)
    log_test("E2E Step 10: Recommendation Engine", is_ok, f"(recs_count={rec_count})")
except Exception as e:
    log_test("E2E Step 10: Recommendation Engine", False, str(e))


# 11. ALERT WEBHOOK DISPATCHER
try:
    res = requests.post(f"{BASE_URL}/api/incidents/test-alert", timeout=10)
    data = res.json()
    is_ok = (res.status_code == 200 and data.get("success") is True)
    log_test("E2E Step 11: Alert Webhook Dispatcher", is_ok, f"(status=dispatched)")
except Exception as e:
    log_test("E2E Step 11: Alert Webhook Dispatcher", False, str(e))


# 12. EXECUTIVE PDF REPORT GENERATION
try:
    res = requests.post(f"{BASE_URL}/api/incidents/generate-report", json={}, timeout=10)
    is_ok = (
        res.status_code == 200 and
        res.headers.get("Content-Type") == "application/pdf" and
        len(res.content) > 1000
    )
    log_test("E2E Step 12: PDF Executive Report", is_ok, f"(pdf_bytes={len(res.content)})")
except Exception as e:
    log_test("E2E Step 12: PDF Executive Report", False, str(e))


# 13. REGIONAL RISK AGGREGATION & MAP MONITORING
try:
    res = requests.get(f"{BASE_URL}/api/regional-status", timeout=10)
    data = res.json()
    reg = data.get("regional", {})
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        "regional_risk" in reg and
        reg.get("sites_monitored") >= 5
    )
    log_test("E2E Step 13: Regional Aggregation", is_ok, f"(regional_risk={reg.get('regional_risk')})")
except Exception as e:
    log_test("E2E Step 13: Regional Aggregation", False, str(e))


print("\n" + "=" * 70)
print("RELIABILITY & FALLBACK RESILIENCE TESTING")
print("=================================================" * 1)

# 14. INVALID SITE ID HANDLING (404)
try:
    res = requests.get(f"{BASE_URL}/api/sites/NON_EXISTENT_SITE_999", timeout=10)
    is_ok = (res.status_code == 404 and res.json().get("success") is False)
    log_test("Reliability: Invalid Site ID (404)", is_ok, f"(status_code={res.status_code})")
except Exception as e:
    log_test("Reliability: Invalid Site ID (404)", False, str(e))

# 15. COORD BOUNDARY VALIDATION (400)
try:
    res = requests.post(f"{BASE_URL}/api/sites", json={"site_id": "ERR", "site_name": "Err", "latitude": 190.0, "longitude": 0.0}, timeout=10)
    is_ok = (res.status_code == 400 and res.json().get("success") is False)
    log_test("Reliability: Out of Bounds Coords (400)", is_ok, f"(status_code={res.status_code})")
except Exception as e:
    log_test("Reliability: Out of Bounds Coords (400)", False, str(e))

# 16. INVALID SCENARIO NAME FALLBACK
try:
    res = requests.post(f"{BASE_URL}/api/telemetry/scenario", json={"scenario": "INVALID_SCENARIO_XYZ"}, timeout=10)
    is_ok = (res.status_code == 400 and res.json().get("success") is False)
    log_test("Reliability: Invalid Scenario Fallback", is_ok, f"(status_code={res.status_code})")
except Exception as e:
    log_test("Reliability: Invalid Scenario Fallback", False, str(e))

# Reset telemetry back to normal
requests.post(f"{BASE_URL}/api/telemetry/scenario", json={"scenario": "NORMAL"}, timeout=10)


print("\n" + "=" * 70)
print("PERFORMANCE AUDIT: EMPIRICAL API LATENCY MEASUREMENTS")
print("=================================================" * 1)

endpoints_to_benchmark = [
    ("/api/realtime-analyze", "GET"),
    ("/api/multi-asset-analyze", "GET"),
    ("/api/regional-status", "GET"),
    ("/api/climate-intelligence", "GET"),
    ("/api/incidents", "GET"),
]

NUM_TRIALS = 15

for ep, method in endpoints_to_benchmark:
    latencies_ms = []
    for _ in range(NUM_TRIALS):
        start_t = time.perf_counter()
        if method == "GET":
            r = requests.get(f"{BASE_URL}{ep}", timeout=10)
        else:
            r = requests.post(f"{BASE_URL}{ep}", json={}, timeout=10)
        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        if r.status_code == 200:
            latencies_ms.append(elapsed_ms)

    if latencies_ms:
        avg_lat = np.mean(latencies_ms)
        p50 = np.percentile(latencies_ms, 50)
        p95 = np.percentile(latencies_ms, 95)
        p99 = np.percentile(latencies_ms, 99)
        print(f"Endpoint: {ep:<25} | Avg: {avg_lat:6.2f}ms | P50: {p50:6.2f}ms | P95: {p95:6.2f}ms | P99: {p99:6.2f}ms")
        log_test(f"Performance Benchmark: {ep}", True, f"(p50={p50:.1f}ms, p95={p95:.1f}ms)")
    else:
        log_test(f"Performance Benchmark: {ep}", False, "(all requests failed)")


print("\n" + "=" * 70)
print(f"E2E AUDIT SUMMARY: {passed} PASSED, {failed} FAILED")
print("=" * 70)

if failed > 0:
    sys.exit(1)
else:
    sys.exit(0)

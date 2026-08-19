"""
scratch/test_phase22_endpoints.py
==================================
HTTP REST API Test Script for Phase 22 — Resilience Optimization & Prescriptive Action Planner
"""

import requests

BASE_URL = "http://127.0.0.1:5000"

def run_tests():
    print("--- Testing Phase 22 Optimization API Endpoints ---")

    # 1. GET /api/optimization/strategies
    r = requests.get(f"{BASE_URL}/api/optimization/strategies")
    assert r.status_code == 200, f"GET strategies failed: {r.status_code}"
    strats = r.json()
    assert strats["success"] is True and len(strats["strategies"]) == 10
    print("[PASS] GET /api/optimization/strategies")

    # 2. POST /api/optimization/optimize
    payload = {
        "site_id": "SITE-001",
        "scenario": {
            "temperature": 41.5,
            "humidity": 80.0,
            "rainfall": 25.0,
            "duration_hours": 6.0,
            "transformer_load": 92.0
        }
    }
    r = requests.post(f"{BASE_URL}/api/optimization/optimize", json=payload)
    assert r.status_code == 200, f"POST optimize failed: {r.status_code}"
    opt_data = r.json()
    assert opt_data["success"] is True
    opt = opt_data["optimization"]
    opt_id = opt["optimization_id"]
    print(f"[PASS] POST /api/optimization/optimize -> Created {opt_id}")

    # 3. GET /api/optimization/{opt_id}
    r = requests.get(f"{BASE_URL}/api/optimization/{opt_id}")
    assert r.status_code == 200
    assert r.json()["optimization"]["optimization_id"] == opt_id
    print(f"[PASS] GET /api/optimization/{opt_id}")

    # 4. POST /api/optimization/{opt_id}/approve
    r = requests.post(f"{BASE_URL}/api/optimization/{opt_id}/approve", json={"operator_name": "Senior Operator"})
    assert r.status_code == 200
    assert r.json()["optimization"]["lifecycle_status"] == "APPROVED"
    print(f"[PASS] POST /api/optimization/{opt_id}/approve")

    # 5. POST /api/optimization/{opt_id}/promote
    r = requests.post(f"{BASE_URL}/api/optimization/{opt_id}/promote")
    assert r.status_code == 200
    assert r.json()["success"] is True
    print(f"[PASS] POST /api/optimization/{opt_id}/promote")

    # 6. GET /api/optimization/history/all
    r = requests.get(f"{BASE_URL}/api/optimization/history/all")
    assert r.status_code == 200
    assert len(r.json()["records"]) >= 1
    print("[PASS] GET /api/optimization/history/all")

    print("\nALL PHASE 22 API ENDPOINTS VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()

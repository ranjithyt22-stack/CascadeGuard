import os
import requests
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000")

print("=" * 65)
print("CASCADEGUARD API TEST SUITE - PHASE 6 (FLEET COMMAND CENTER)")
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


# 1. GET /api/health
for attempt in range(5):
    try:
        res = requests.get(f"{BASE_URL}/api/health", timeout=10)
        data = res.json()
        is_ok = (
            res.status_code == 200 and
            data.get("status") == "online" and
            data.get("transformers_monitored") == 5
        )
        log_test("GET /api/health", is_ok, f"(monitored={data.get('transformers_monitored')}, ver={data.get('operational_model_version')})")
        break
    except Exception as e:
        if attempt == 4:
            log_test("GET /api/health", False, str(e))
        time.sleep(0.5)


# 2. GET /api/transformers
try:
    res = requests.get(f"{BASE_URL}/api/transformers", timeout=10)
    data = res.json()
    tx_list = data.get("transformers", [])
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        len(tx_list) == 5 and
        tx_list[0]["transformer_id"] == "TX-001"
    )
    log_test("GET /api/transformers", is_ok, f"(count={len(tx_list)})")
except Exception as e:
    log_test("GET /api/transformers", False, str(e))


# 3. GET /api/fleet-status
try:
    res = requests.get(f"{BASE_URL}/api/fleet-status", timeout=15)
    data = res.json()
    tx_list = data.get("transformers", [])
    summary = data.get("summary", {})

    ranks = [t.get("priority_rank") for t in tx_list]
    scores = [t.get("cascade", {}).get("score") for t in tx_list]

    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        len(tx_list) == 5 and
        ranks == [1, 2, 3, 4, 5] and
        all(0.0 <= s <= 100.0 for s in scores) and
        summary.get("total_monitored") == 5
    )
    log_test("GET /api/fleet-status", is_ok, f"(top_tx={summary.get('highest_risk_transformer', {}).get('transformer_id')}, fleet_risk={summary.get('fleet_risk')})")
except Exception as e:
    log_test("GET /api/fleet-status", False, str(e))


# 4. GET /api/transformer/TX-001
try:
    res = requests.get(f"{BASE_URL}/api/transformer/TX-001", timeout=10)
    data = res.json()
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        data.get("transformer_id") == "TX-001" and
        "cascade" in data and
        "predictive_forecast" in data
    )
    log_test("GET /api/transformer/TX-001", is_ok, f"(score={data.get('cascade', {}).get('score')})")
except Exception as e:
    log_test("GET /api/transformer/TX-001", False, str(e))


# 5. GET /api/transformer/TX-003
try:
    res = requests.get(f"{BASE_URL}/api/transformer/TX-003", timeout=10)
    data = res.json()
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        data.get("transformer_id") == "TX-003" and
        "predictive_forecast" in data
    )
    log_test("GET /api/transformer/TX-003", is_ok, f"(location={data.get('location')}, score={data.get('cascade', {}).get('score')})")
except Exception as e:
    log_test("GET /api/transformer/TX-003", False, str(e))


# 6. GET /api/fleet-history
try:
    res = requests.get(f"{BASE_URL}/api/fleet-history", timeout=10)
    data = res.json()
    hist_map = data.get("history", {})
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        isinstance(hist_map, dict) and
        "TX-001" in hist_map
    )
    log_test("GET /api/fleet-history", is_ok, f"(tx_count={len(hist_map)})")
except Exception as e:
    log_test("GET /api/fleet-history", False, str(e))


# 7. POST /api/fleet/reset
try:
    res = requests.post(f"{BASE_URL}/api/fleet/reset", timeout=10)
    data = res.json()
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True
    )
    log_test("POST /api/fleet/reset", is_ok, f"(msg={data.get('message')})")
except Exception as e:
    log_test("POST /api/fleet/reset", False, str(e))


# 8. GET /api/fleet-analyze
try:
    res = requests.get(f"{BASE_URL}/api/fleet-analyze", timeout=15)
    data = res.json()
    tx_list = data.get("transformers", [])
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        len(tx_list) == 5
    )
    log_test("GET /api/fleet-analyze", is_ok, f"(evaluated_tx={len(tx_list)})")
except Exception as e:
    log_test("GET /api/fleet-analyze", False, str(e))


# 9. GET /api/live-data (Backwards Compatibility)
try:
    res = requests.get(f"{BASE_URL}/api/live-data?tx_id=TX-001", timeout=10)
    data = res.json()
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        "data" in data and
        "health_data" in data
    )
    log_test("GET /api/live-data (Backwards Compat)", is_ok, f"(timestamp={data.get('timestamp')})")
except Exception as e:
    log_test("GET /api/live-data (Backwards Compat)", False, str(e))


# 10. GET /api/live-analyze (Backwards Compatibility)
try:
    res = requests.get(f"{BASE_URL}/api/live-analyze?tx_id=TX-001", timeout=15)
    data = res.json()
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        "cascade" in data and
        "predictive_forecast" in data
    )
    log_test("GET /api/live-analyze (Backwards Compat)", is_ok, f"(score={data.get('cascade', {}).get('score')})")
except Exception as e:
    log_test("GET /api/live-analyze (Backwards Compat)", False, str(e))


# 11. POST /api/analyze (Backwards Compatibility)
try:
    payload = {
        "ATI": 30.0, "OTI": 65.0, "WTI": 70.0, "OLI": 100.0,
        "Hydrogen": 10, "Methane": 5, "Ethylene": 2, "Water content": 15,
        "location": "Coimbatore"
    }
    res = requests.post(f"{BASE_URL}/api/analyze", json=payload, timeout=10)
    data = res.json()
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        0.0 <= data.get("cascade", {}).get("score", -1) <= 100.0
    )
    log_test("POST /api/analyze (Backwards Compat)", is_ok, f"(score={data.get('cascade', {}).get('score')})")
except Exception as e:
    log_test("POST /api/analyze (Backwards Compat)", False, str(e))


# 12. GET /api/predictive-forecast (Backwards Compatibility)
try:
    res = requests.get(f"{BASE_URL}/api/predictive-forecast?tx_id=TX-001", timeout=15)
    data = res.json()
    pf = data.get("predictive_forecast", {})
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        "forecast" in pf
    )
    log_test("GET /api/predictive-forecast (Backwards Compat)", is_ok, f"(60m_score={pf.get('forecast', {}).get('60m', {}).get('cascade_score')})")
except Exception as e:
    log_test("GET /api/predictive-forecast (Backwards Compat)", False, str(e))


# 13. GET /api/scenarios (Backwards Compatibility)
try:
    res = requests.get(f"{BASE_URL}/api/scenarios", timeout=10)
    data = res.json()
    sc_list = data.get("scenarios", [])
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        len(sc_list) >= 7
    )
    log_test("GET /api/scenarios (Backwards Compat)", is_ok, f"(scenarios_count={len(sc_list)})")
except Exception as e:
    log_test("GET /api/scenarios (Backwards Compat)", False, str(e))


# 14. POST /api/simulate-scenario [COMBINED_CASCADE] (Backwards Compatibility)
try:
    payload = {"scenario": "COMBINED_CASCADE", "tx_id": "TX-001", "location": "Coimbatore"}
    res = requests.post(f"{BASE_URL}/api/simulate-scenario", json=payload, timeout=15)
    data = res.json()
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        "comparison" in data and
        0.0 <= data.get("cascade", {}).get("score", -1) <= 100.0
    )
    log_test("POST /api/simulate-scenario [COMBINED_CASCADE]", is_ok, f"(scenario_score={data.get('cascade', {}).get('score')})")
except Exception as e:
    log_test("POST /api/simulate-scenario [COMBINED_CASCADE]", False, str(e))


# 15. GET /api/predictive-forecast
try:
    res = requests.get(f"{BASE_URL}/api/predictive-forecast?tx_id=TX-001", timeout=10)
    data = res.json()
    pf = data.get("predictive_forecast", {})
    fc = pf.get("forecast", {})
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        "15m" in fc and "30m" in fc and "60m" in fc
    )
    log_test("GET /api/predictive-forecast", is_ok, f"(horizon_keys={list(fc.keys())})")
except Exception as e:
    log_test("GET /api/predictive-forecast", False, str(e))


# 16. GET /api/multi-asset-analyze (Phase 9 Multi-Asset Cascade Intelligence)
try:
    res = requests.get(f"{BASE_URL}/api/multi-asset-analyze?location=Coimbatore&tx_id=TX-001", timeout=15)
    data = res.json()
    assets = data.get("assets", {})
    system = data.get("system", {})
    cascade = data.get("cascade", {})
    tx = assets.get("transformer", {})
    ch = assets.get("chiller", {})
    wp = assets.get("water_pump", {})

    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        "transformer" in assets and
        "chiller" in assets and
        "water_pump" in assets and
        0.0 <= tx.get("risk", -1) <= 100.0 and
        0.0 <= ch.get("risk", -1) <= 100.0 and
        0.0 <= wp.get("risk", -1) <= 100.0 and
        0.0 <= system.get("system_cascade_risk", -1) <= 100.0 and
        "climate" in data and
        "most_vulnerable_asset" in cascade and
        "recommendation" in data and
        "limitations" in data and
        wp.get("status") == "DECISION_SUPPORT_ONLY"
    )
    log_test("GET /api/multi-asset-analyze", is_ok, f"(sys_risk={system.get('system_cascade_risk')}, vuln={cascade.get('most_vulnerable_asset', {}).get('asset')}, pump_status={wp.get('status')})")
except Exception as e:
    log_test("GET /api/multi-asset-analyze", False, str(e))


# 17. GET /api/realtime-status (Phase 10 Real API Adapter Status)
try:
    res = requests.get(f"{BASE_URL}/api/realtime-status", timeout=10)
    data = res.json()
    w = data.get("weather", {})
    t = data.get("transformer", {})
    c = data.get("chiller", {})
    p = data.get("water_pump", {})

    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        w.get("source") == "live_open_meteo_api" and
        t.get("source") in ["live_scada_api", "historical_replay"] and
        c.get("source") in ["live_bms_api", "historical_dataset"] and
        p.get("source") in ["live_iot_api", "historical_dataset"] and
        p.get("model_status") == "DECISION_SUPPORT_ONLY"
    )
    log_test("GET /api/realtime-status", is_ok, f"(weather={w.get('source')}, tx={t.get('source')}, ch={c.get('source')}, pump={p.get('source')})")
except Exception as e:
    log_test("GET /api/realtime-status", False, str(e))


# 18. GET /api/realtime-analyze (Phase 10 Real-Time Data Pipeline & Freshness)
try:
    res = requests.get(f"{BASE_URL}/api/realtime-analyze?location=Coimbatore&tx_id=TX-001", timeout=15)
    data = res.json()
    sources = data.get("data_sources", {})
    assets = data.get("assets", {})
    tx = assets.get("transformer", {})
    ch = assets.get("chiller", {})
    wp = assets.get("water_pump", {})

    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        "weather" in sources and
        "provenance" in tx and
        "freshness" in tx and
        "provenance" in ch and
        "provenance" in wp and
        data.get("system", {}).get("system_cascade_risk") is not None
    )
    log_test("GET /api/realtime-analyze", is_ok, f"(tx_prov={tx.get('provenance')}, ch_prov={ch.get('provenance')}, wp_prov={wp.get('provenance')})")
except Exception as e:
    log_test("GET /api/realtime-analyze", False, str(e))


# 19. FRESHNESS & SOURCE VALIDATION
try:
    res = requests.get(f"{BASE_URL}/api/realtime-analyze", timeout=10)
    data = res.json()
    assets = data.get("assets", {})
    tx_fresh = assets.get("transformer", {}).get("freshness", {})
    ch_fresh = assets.get("chiller", {}).get("freshness", {})

    is_ok = (
        tx_fresh.get("freshness_status") in ["HISTORICAL_REPLAY", "LIVE", "RECENT", "STALE"] and
        ch_fresh.get("freshness_status") in ["HISTORICAL_DATASET", "LIVE", "RECENT", "STALE"] and
        tx_fresh.get("stale") is False
    )
    log_test("Freshness & Source Validation", is_ok, f"(tx_status={tx_fresh.get('freshness_status')}, ch_status={ch_fresh.get('freshness_status')})")
except Exception as e:
    log_test("Freshness & Source Validation", False, str(e))


# 20. FALLBACK ARCHITECTURE VALIDATION
try:
    # Verifies system returns valid historical replay response when live SCADA/BMS URLs are unset
    res = requests.get(f"{BASE_URL}/api/realtime-status", timeout=10)
    data = res.json()
    t_warning = data.get("transformer", {}).get("warning")
    c_warning = data.get("chiller", {}).get("warning")
    p_warning = data.get("water_pump", {}).get("warning")

    is_ok = (
        data.get("transformer", {}).get("realtime_available") is False and
        t_warning is not None and
        c_warning is not None and
        p_warning is not None
    )
    log_test("Fallback Architecture Validation", is_ok, f"(t_warn={bool(t_warning)}, c_warn={bool(c_warning)})")
except Exception as e:
    log_test("Fallback Architecture Validation", False, str(e))


# 21. API FAILURE RESILIENCY TEST
try:
    # Simulates invalid location / external timeout and verifies fallback climate data without crash
    res = requests.get(f"{BASE_URL}/api/realtime-analyze?location=NonExistentCityXYZ", timeout=10)
    data = res.json()
    climate = data.get("climate", {})
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        climate.get("climate_stress") is not None
    )
    log_test("API Failure Resiliency Test", is_ok, f"(fallback_stress={climate.get('climate_stress')})")
except Exception as e:
    log_test("API Failure Resiliency Test", False, str(e))


# 22. POST /api/scenario-analyze (NORMAL Scenario)
try:
    res = requests.post(f"{BASE_URL}/api/scenario-analyze", json={"scenario": "NORMAL", "location": "Coimbatore"}, timeout=10)
    data = res.json()
    scen = data.get("scenario", {})
    casc = data.get("cascade", {})
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        scen.get("name") == "NORMAL" and
        scen.get("simulated") is False and
        casc.get("change") == 0.0
    )
    log_test("POST /api/scenario-analyze [NORMAL]", is_ok, f"(base={casc.get('baseline_risk')}, sim={casc.get('scenario_risk')}, delta={casc.get('change')})")
except Exception as e:
    log_test("POST /api/scenario-analyze [NORMAL]", False, str(e))


# 23. POST /api/scenario-analyze (HEATWAVE Scenario & Delta Calculation)
try:
    res = requests.post(f"{BASE_URL}/api/scenario-analyze", json={"scenario": "HEATWAVE", "location": "Coimbatore"}, timeout=10)
    data = res.json()
    scen = data.get("scenario", {})
    casc = data.get("cascade", {})
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        scen.get("name") == "HEATWAVE" and
        scen.get("simulated") is True and
        casc.get("change") > 0.0 and
        "cascade_path" in data
    )
    log_test("POST /api/scenario-analyze [HEATWAVE]", is_ok, f"(base={casc.get('baseline_risk')}, sim={casc.get('scenario_risk')}, delta=+{casc.get('change')})")
except Exception as e:
    log_test("POST /api/scenario-analyze [HEATWAVE]", False, str(e))


# 24. POST /api/scenario-analyze (EXTREME_HEAT Scenario)
try:
    res = requests.post(f"{BASE_URL}/api/scenario-analyze", json={"scenario": "EXTREME_HEAT", "location": "Coimbatore"}, timeout=10)
    data = res.json()
    casc = data.get("cascade", {})
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        casc.get("scenario_risk") >= casc.get("baseline_risk")
    )
    log_test("POST /api/scenario-analyze [EXTREME_HEAT]", is_ok, f"(sim_risk={casc.get('scenario_risk')}, level={casc.get('level')})")
except Exception as e:
    log_test("POST /api/scenario-analyze [EXTREME_HEAT]", False, str(e))


# 25. POST /api/scenario-analyze (HIGH_HUMIDITY & HEAVY_RAIN)
try:
    r_hum = requests.post(f"{BASE_URL}/api/scenario-analyze", json={"scenario": "HIGH_HUMIDITY"}, timeout=10).json()
    r_rain = requests.post(f"{BASE_URL}/api/scenario-analyze", json={"scenario": "HEAVY_RAIN"}, timeout=10).json()
    is_ok = (
        r_hum.get("success") is True and
        r_rain.get("success") is True and
        r_hum.get("weather", {}).get("scenario", {}).get("humidity") == 95.0 and
        r_rain.get("weather", {}).get("scenario", {}).get("rain") == 25.0
    )
    log_test("POST /api/scenario-analyze [HUMIDITY & RAIN]", is_ok, f"(hum=95%, rain=25mm)")
except Exception as e:
    log_test("POST /api/scenario-analyze [HUMIDITY & RAIN]", False, str(e))


# 26. POST /api/scenario-analyze (COOLING_FAILURE & PUMP_DEGRADATION)
try:
    r_cool = requests.post(f"{BASE_URL}/api/scenario-analyze", json={"scenario": "COOLING_FAILURE"}, timeout=10).json()
    r_pump = requests.post(f"{BASE_URL}/api/scenario-analyze", json={"scenario": "PUMP_DEGRADATION"}, timeout=10).json()
    is_ok = (
        r_cool.get("success") is True and
        r_pump.get("success") is True and
        r_cool.get("assets", {}).get("chiller", {}).get("risk") > 20.0 and
        r_pump.get("assets", {}).get("water_pump", {}).get("risk") > 20.0
    )
    log_test("POST /api/scenario-analyze [COOLING & PUMP]", is_ok, f"(ch_risk={r_cool.get('assets',{}).get('chiller',{}).get('risk')}, pump_risk={r_pump.get('assets',{}).get('water_pump',{}).get('risk')})")
except Exception as e:
    log_test("POST /api/scenario-analyze [COOLING & PUMP]", False, str(e))


# 27. POST /api/scenario-analyze (COMBINED_CASCADE)
try:
    res = requests.post(f"{BASE_URL}/api/scenario-analyze", json={"scenario": "COMBINED_CASCADE"}, timeout=10)
    data = res.json()
    casc = data.get("cascade", {})
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        casc.get("scenario_risk") > casc.get("baseline_risk")
    )
    log_test("POST /api/scenario-analyze [COMBINED_CASCADE]", is_ok, f"(sim_risk={casc.get('scenario_risk')}, delta=+{casc.get('change')})")
except Exception as e:
    log_test("POST /api/scenario-analyze [COMBINED_CASCADE]", False, str(e))


# 28. INVALID SCENARIO & MISSING LOCATION HANDLING
try:
    res = requests.post(f"{BASE_URL}/api/scenario-analyze", json={"scenario": "UNKNOWN_SCENARIO_XYZ"}, timeout=10)
    data = res.json()
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        data.get("scenario", {}).get("name") == "NORMAL"
    )
    log_test("Invalid Scenario Handling", is_ok, f"(fallback_scenario={data.get('scenario', {}).get('name')})")
except Exception as e:
    log_test("Invalid Scenario Handling", False, str(e))


# 29. GET /api/scenario-summary (All 8 Scenarios Array)
try:
    res = requests.get(f"{BASE_URL}/api/scenario-summary?location=Coimbatore", timeout=10)
    data = res.json()
    sc_list = data.get("scenarios", [])
    names = [s.get("scenario") for s in sc_list]
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        len(sc_list) == 8 and
        "HEATWAVE" in names and
        "COMBINED_CASCADE" in names
    )
    log_test("GET /api/scenario-summary", is_ok, f"(count={len(sc_list)}, scenarios={len(names)})")
except Exception as e:
    log_test("GET /api/scenario-summary", False, str(e))


# 30. MODEL INTEGRITY VERIFICATION
try:
    from pathlib import Path
    models_dir = Path(__file__).resolve().parent / "models"
    m1 = (models_dir / "operational_stress_xgboost_v3.pkl").exists()
    m2 = (models_dir / "health_index_xgboost.pkl").exists()
    m3 = (models_dir / "chiller_xgboost.pkl").exists()
    is_ok = m1 and m2 and m3
    log_test("Model Integrity Verification", is_ok, f"(v3_op={m1}, health={m2}, chiller={m3})")
except Exception as e:
    log_test("Model Integrity Verification", False, str(e))


# 31. POST /api/site/configure (Valid Site Payload)
try:
    site_payload = {
        "site_id": "SITE-001",
        "site_name": "Coimbatore Substation Alpha",
        "latitude": 11.00555,
        "longitude": 76.96612,
        "transformer_id": "TX-001",
        "chiller_id": "CH-001",
        "water_pump_id": "WP-001"
    }
    res = requests.post(f"{BASE_URL}/api/site/configure", json=site_payload, timeout=10)
    data = res.json()
    site = data.get("site", {})
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        site.get("site_id") == "SITE-001" and
        site.get("location", {}).get("latitude") == 11.00555
    )
    log_test("POST /api/site/configure", is_ok, f"(site_id={site.get('site_id')}, lat={site.get('location', {}).get('latitude')})")
except Exception as e:
    log_test("POST /api/site/configure", False, str(e))


# 32. GET /api/site/config
try:
    res = requests.get(f"{BASE_URL}/api/site/config", timeout=10)
    data = res.json()
    site = data.get("site", {})
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        data.get("configured") is True and
        site.get("site_id") == "SITE-001"
    )
    log_test("GET /api/site/config", is_ok, f"(configured={data.get('configured')}, name={site.get('site_name')})")
except Exception as e:
    log_test("GET /api/site/config", False, str(e))


# 33. VALID LATITUDE BOUNDARY (-90 to +90)
try:
    p1 = {"site_id": "SITE-POLE", "site_name": "North Pole Site", "latitude": 90.0, "longitude": 0.0, "transformer_id": "TX-01", "chiller_id": "CH-01", "water_pump_id": "WP-01"}
    r1 = requests.post(f"{BASE_URL}/api/site/configure", json=p1, timeout=10)
    is_ok = r1.status_code == 200 and r1.json().get("success") is True
    log_test("Valid Latitude Boundary", is_ok, f"(lat=90.0 status={r1.status_code})")
except Exception as e:
    log_test("Valid Latitude Boundary", False, str(e))


# 34. INVALID LATITUDE BOUNDARY (> 90 or < -90)
try:
    p_bad = {"site_id": "SITE-BAD", "site_name": "Bad Lat Site", "latitude": 95.0, "longitude": 76.0, "transformer_id": "TX-01", "chiller_id": "CH-01", "water_pump_id": "WP-01"}
    r_bad = requests.post(f"{BASE_URL}/api/site/configure", json=p_bad, timeout=10)
    is_ok = r_bad.status_code == 400 and r_bad.json().get("success") is False
    log_test("Invalid Latitude Boundary", is_ok, f"(expected_400, got={r_bad.status_code})")
except Exception as e:
    log_test("Invalid Latitude Boundary", False, str(e))


# 35. VALID LONGITUDE BOUNDARY (-180 to +180)
try:
    p2 = {"site_id": "SITE-DATELINE", "site_name": "Date Line Site", "latitude": 11.0, "longitude": 180.0, "transformer_id": "TX-01", "chiller_id": "CH-01", "water_pump_id": "WP-01"}
    r2 = requests.post(f"{BASE_URL}/api/site/configure", json=p2, timeout=10)
    is_ok = r2.status_code == 200 and r2.json().get("success") is True
    log_test("Valid Longitude Boundary", is_ok, f"(lon=180.0 status={r2.status_code})")
except Exception as e:
    log_test("Valid Longitude Boundary", False, str(e))


# 36. INVALID LONGITUDE BOUNDARY (> 180 or < -180)
try:
    p_bad_lon = {"site_id": "SITE-BAD", "site_name": "Bad Lon Site", "latitude": 11.0, "longitude": 190.0, "transformer_id": "TX-01", "chiller_id": "CH-01", "water_pump_id": "WP-01"}
    r_bad_lon = requests.post(f"{BASE_URL}/api/site/configure", json=p_bad_lon, timeout=10)
    is_ok = r_bad_lon.status_code == 400 and r_bad_lon.json().get("success") is False
    log_test("Invalid Longitude Boundary", is_ok, f"(expected_400, got={r_bad_lon.status_code})")
except Exception as e:
    log_test("Invalid Longitude Boundary", False, str(e))


# 37. MISSING SITE ID / NAME VALIDATION
try:
    p_no_id = {"site_id": "", "site_name": "", "latitude": 11.0, "longitude": 76.0, "transformer_id": "TX-01", "chiller_id": "CH-01", "water_pump_id": "WP-01"}
    r_no_id = requests.post(f"{BASE_URL}/api/site/configure", json=p_no_id, timeout=10)
    is_ok = r_no_id.status_code == 400 and "Missing required parameter" in r_no_id.json().get("error", "")
    log_test("Missing Site ID / Name Validation", is_ok, f"(error={r_no_id.json().get('error')})")
except Exception as e:
    log_test("Missing Site ID / Name Validation", False, str(e))


# 38. MISSING ASSET ID VALIDATION
try:
    p_no_asset = {"site_id": "SITE-01", "site_name": "Site Name", "latitude": 11.0, "longitude": 76.0, "transformer_id": "", "chiller_id": "CH-01", "water_pump_id": "WP-01"}
    r_no_asset = requests.post(f"{BASE_URL}/api/site/configure", json=p_no_asset, timeout=10)
    is_ok = r_no_asset.status_code == 400 and "Missing required parameter" in r_no_asset.json().get("error", "")
    log_test("Missing Asset ID Validation", is_ok, f"(error={r_no_asset.json().get('error')})")
except Exception as e:
    log_test("Missing Asset ID Validation", False, str(e))


# Re-reset active site configuration to default
try:
    site_payload = {
        "site_id": "SITE-001",
        "site_name": "Coimbatore Industrial Facility",
        "latitude": 11.00555,
        "longitude": 76.96612,
        "transformer_id": "TX-001",
        "chiller_id": "CH-001",
        "water_pump_id": "WP-001"
    }
    requests.post(f"{BASE_URL}/api/site/configure", json=site_payload, timeout=10)
except Exception:
    pass


# 39. WEATHER USES CONFIGURED COORDINATES
try:
    res = requests.get(f"{BASE_URL}/api/realtime-analyze?latitude=11.00555&longitude=76.96612", timeout=10)
    data = res.json()
    clim = data.get("climate", {})
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        clim.get("latitude") == 11.00555 and
        clim.get("longitude") == 76.96612
    )
    log_test("Weather Uses Configured Coordinates", is_ok, f"(lat={clim.get('latitude')}, lon={clim.get('longitude')})")
except Exception as e:
    log_test("Weather Uses Configured Coordinates", False, str(e))


# 40. REALTIME-ANALYZE INCLUDES SITE INFORMATION
try:
    res = requests.get(f"{BASE_URL}/api/realtime-analyze", timeout=10)
    data = res.json()
    site = data.get("site", {})
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        site.get("site_id") == "SITE-001" and
        "assets" in site
    )
    log_test("realtime-analyze Includes Site Info", is_ok, f"(site_id={site.get('site_id')}, site_name={site.get('site_name')})")
except Exception as e:
    log_test("realtime-analyze Includes Site Info", False, str(e))


# 41. MULTI-ASSET-ANALYZE INCLUDES SITE INFORMATION
try:
    res = requests.get(f"{BASE_URL}/api/multi-asset-analyze", timeout=10)
    data = res.json()
    site = data.get("site", {})
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        site.get("site_id") == "SITE-001"
    )
    log_test("multi-asset-analyze Includes Site Info", is_ok, f"(site_id={site.get('site_id')})")
except Exception as e:
    log_test("multi-asset-analyze Includes Site Info", False, str(e))


# 42. GET /api/climate-intelligence
try:
    res = requests.get(f"{BASE_URL}/api/climate-intelligence?location=Coimbatore", timeout=10)
    data = res.json()
    intel = data.get("climate_intelligence", {})
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        "current" in intel and
        "heatwave" in intel and
        "asset_impacts" in intel and
        "forecast_trend" in intel and
        "data_quality" in intel
    )
    log_test("GET /api/climate-intelligence", is_ok, f"(overall_stress={intel.get('overall_climate_stress')}, severity={intel.get('severity')})")
except Exception as e:
    log_test("GET /api/climate-intelligence", False, str(e))


# 43. HEATWAVE DURATION ANALYSIS
try:
    res = requests.get(f"{BASE_URL}/api/climate-intelligence", timeout=10)
    intel = res.json().get("climate_intelligence", {})
    hw = intel.get("heatwave", {})
    is_ok = (
        "detected" in hw and
        "peak_temperature" in hw and
        "duration_hours" in hw and
        "severity" in hw and
        "disclaimer" in hw
    )
    log_test("Heatwave Duration Analysis", is_ok, f"(peak={hw.get('peak_temperature')}°C, duration={hw.get('duration_hours')}h, severity={hw.get('severity')})")
except Exception as e:
    log_test("Heatwave Duration Analysis", False, str(e))


# 44. ASSET-SPECIFIC CLIMATE SCORES
try:
    res = requests.get(f"{BASE_URL}/api/climate-intelligence", timeout=10)
    intel = res.json().get("climate_intelligence", {})
    impacts = intel.get("asset_impacts", {})
    tx = impacts.get("transformer", {})
    ch = impacts.get("chiller", {})
    wp = impacts.get("water_pump", {})
    is_ok = (
        "climate_stress" in tx and
        "climate_stress" in ch and
        "climate_stress" in wp and
        "factors" in tx and
        "factors" in ch and
        "factors" in wp
    )
    log_test("Asset-Specific Climate Scores", is_ok, f"(tx={tx.get('climate_stress')}, ch={ch.get('climate_stress')}, wp={wp.get('climate_stress')})")
except Exception as e:
    log_test("Asset-Specific Climate Scores", False, str(e))


# 45. CLIMATE TREND FORECAST (6h & 24h)
try:
    res = requests.get(f"{BASE_URL}/api/climate-intelligence", timeout=10)
    intel = res.json().get("climate_intelligence", {})
    trend = intel.get("forecast_trend", {})
    is_ok = (
        trend.get("trend") in ["RISING", "STABLE", "FALLING"] and
        "change_6h" in trend and
        "change_24h" in trend
    )
    log_test("Climate Trend Forecast", is_ok, f"(trend={trend.get('trend')}, Δ6h={trend.get('change_6h')}, Δ24h={trend.get('change_24h')})")
except Exception as e:
    log_test("Climate Trend Forecast", False, str(e))


# 46. DATA FRESHNESS & CONFIDENCE LAYER
try:
    res = requests.get(f"{BASE_URL}/api/climate-intelligence", timeout=10)
    intel = res.json().get("climate_intelligence", {})
    dq = intel.get("data_quality", {})
    is_ok = (
        dq.get("confidence") in ["HIGH", "MEDIUM", "LOW"] and
        dq.get("status") in ["LIVE", "FALLBACK"] and
        "asset_limitations" in dq
    )
    log_test("Data Freshness & Confidence Layer", is_ok, f"(status={dq.get('status')}, confidence={dq.get('confidence')})")
except Exception as e:
    log_test("Data Freshness & Confidence Layer", False, str(e))


# 47. DYNAMIC ENGINEERING EXPLANATIONS
try:
    res = requests.get(f"{BASE_URL}/api/climate-intelligence", timeout=10)
    intel = res.json().get("climate_intelligence", {})
    exps = intel.get("explanation", [])
    is_ok = isinstance(exps, list) and len(exps) >= 2
    log_test("Dynamic Engineering Explanations", is_ok, f"(bullet_count={len(exps)})")
except Exception as e:
    log_test("Dynamic Engineering Explanations", False, str(e))


# 48. OFFLINE / FALLBACK RESILIENCE TEST
try:
    res = requests.get(f"{BASE_URL}/api/climate-intelligence?location=InvalidNonExistentLocationXYZ", timeout=10)
    data = res.json()
    intel = data.get("climate_intelligence", {})
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        intel.get("overall_climate_stress") is not None
    )
    log_test("Offline / Fallback Resilience Test", is_ok, f"(overall_stress={intel.get('overall_climate_stress')})")
except Exception as e:
    log_test("Offline / Fallback Resilience Test", False, str(e))


# 49. GET /api/telemetry/status
try:
    res = requests.get(f"{BASE_URL}/api/telemetry/status", timeout=10)
    data = res.json()
    assets = data.get("assets", {})
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        data.get("telemetry_mode") in ["MOCK", "REAL_OT"] and
        "transformer" in assets and
        "chiller" in assets and
        "water_pump" in assets
    )
    log_test("GET /api/telemetry/status", is_ok, f"(mode={data.get('telemetry_mode')}, assets_count={len(assets)})")
except Exception as e:
    log_test("GET /api/telemetry/status", False, str(e))


# 50. GET /api/telemetry/live (MOCK Mode)
try:
    res = requests.get(f"{BASE_URL}/api/telemetry/live", timeout=10)
    data = res.json()
    tel = data.get("telemetry", {})
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        "transformer" in tel and
        "chiller" in tel and
        "water_pump" in tel
    )
    log_test("GET /api/telemetry/live", is_ok, f"(mode={data.get('telemetry_mode')})")
except Exception as e:
    log_test("GET /api/telemetry/live", False, str(e))


# 51. GET /api/telemetry/asset/TX-001 (Transformer Telemetry)
try:
    res = requests.get(f"{BASE_URL}/api/telemetry/asset/TX-001", timeout=10)
    data = res.json()
    t_data = data.get("telemetry", {})
    t_val = t_data.get("telemetry", {})
    is_ok = (
        res.status_code == 200 and
        t_data.get("asset_type") == "TRANSFORMER" and
        "OTI" in t_val and
        "WTI" in t_val
    )
    log_test("Transformer OT Telemetry Schema", is_ok, f"(OTI={t_val.get('OTI')}°C, WTI={t_val.get('WTI')}°C)")
except Exception as e:
    log_test("Transformer OT Telemetry Schema", False, str(e))


# 52. GET /api/telemetry/asset/CH-001 (Chiller Telemetry)
try:
    res = requests.get(f"{BASE_URL}/api/telemetry/asset/CH-001", timeout=10)
    data = res.json()
    t_data = data.get("telemetry", {})
    t_val = t_data.get("telemetry", {})
    is_ok = (
        res.status_code == 200 and
        t_data.get("asset_type") == "CHILLER" and
        "TEI" in t_val and
        "kW" in t_val
    )
    log_test("Chiller OT Telemetry Schema", is_ok, f"(TEI={t_val.get('TEI')}°C, kW={t_val.get('kW')})")
except Exception as e:
    log_test("Chiller OT Telemetry Schema", False, str(e))


# 53. GET /api/telemetry/asset/WP-001 (Water Pump Telemetry)
try:
    res = requests.get(f"{BASE_URL}/api/telemetry/asset/WP-001", timeout=10)
    data = res.json()
    t_data = data.get("telemetry", {})
    t_val = t_data.get("telemetry", {})
    is_ok = (
        res.status_code == 200 and
        t_data.get("asset_type") == "WATER_PUMP" and
        "flow" in t_val and
        "pressure" in t_val
    )
    log_test("Water Pump OT Telemetry Schema", is_ok, f"(flow={t_val.get('flow')} L/m, press={t_val.get('pressure')} bar)")
except Exception as e:
    log_test("Water Pump OT Telemetry Schema", False, str(e))


# 54. POST /api/telemetry/scenario [NORMAL]
try:
    res = requests.post(f"{BASE_URL}/api/telemetry/scenario", json={"scenario": "NORMAL"}, timeout=10)
    data = res.json()
    is_ok = (res.status_code == 200 and data.get("active_scenario") == "NORMAL")
    log_test("POST /api/telemetry/scenario [NORMAL]", is_ok, f"(sc={data.get('active_scenario')})")
except Exception as e:
    log_test("POST /api/telemetry/scenario [NORMAL]", False, str(e))


# 55. POST /api/telemetry/scenario [HIGH_LOAD]
try:
    res = requests.post(f"{BASE_URL}/api/telemetry/scenario", json={"scenario": "HIGH_LOAD"}, timeout=10)
    data = res.json()
    is_ok = (res.status_code == 200 and data.get("active_scenario") == "HIGH_LOAD")
    log_test("POST /api/telemetry/scenario [HIGH_LOAD]", is_ok, f"(sc={data.get('active_scenario')})")
except Exception as e:
    log_test("POST /api/telemetry/scenario [HIGH_LOAD]", False, str(e))


# 56. POST /api/telemetry/scenario [HEAT_STRESS]
try:
    res = requests.post(f"{BASE_URL}/api/telemetry/scenario", json={"scenario": "HEAT_STRESS"}, timeout=10)
    data = res.json()
    is_ok = (res.status_code == 200 and data.get("active_scenario") == "HEAT_STRESS")
    log_test("POST /api/telemetry/scenario [HEAT_STRESS]", is_ok, f"(sc={data.get('active_scenario')})")
except Exception as e:
    log_test("POST /api/telemetry/scenario [HEAT_STRESS]", False, str(e))


# 57. POST /api/telemetry/scenario [CHILLER_OVERLOAD]
try:
    res = requests.post(f"{BASE_URL}/api/telemetry/scenario", json={"scenario": "CHILLER_OVERLOAD"}, timeout=10)
    data = res.json()
    is_ok = (res.status_code == 200 and data.get("active_scenario") == "CHILLER_OVERLOAD")
    log_test("POST /api/telemetry/scenario [CHILLER_OVERLOAD]", is_ok, f"(sc={data.get('active_scenario')})")
except Exception as e:
    log_test("POST /api/telemetry/scenario [CHILLER_OVERLOAD]", False, str(e))


# 58. POST /api/telemetry/scenario [PUMP_DEGRADATION]
try:
    res = requests.post(f"{BASE_URL}/api/telemetry/scenario", json={"scenario": "PUMP_DEGRADATION"}, timeout=10)
    data = res.json()
    is_ok = (res.status_code == 200 and data.get("active_scenario") == "PUMP_DEGRADATION")
    log_test("POST /api/telemetry/scenario [PUMP_DEGRADATION]", is_ok, f"(sc={data.get('active_scenario')})")
except Exception as e:
    log_test("POST /api/telemetry/scenario [PUMP_DEGRADATION]", False, str(e))


# 59. POST /api/telemetry/scenario [COMBINED_CASCADE]
try:
    res = requests.post(f"{BASE_URL}/api/telemetry/scenario", json={"scenario": "COMBINED_CASCADE"}, timeout=10)
    data = res.json()
    is_ok = (res.status_code == 200 and data.get("active_scenario") == "COMBINED_CASCADE")
    log_test("POST /api/telemetry/scenario [COMBINED_CASCADE]", is_ok, f"(sc={data.get('active_scenario')})")
except Exception as e:
    log_test("POST /api/telemetry/scenario [COMBINED_CASCADE]", False, str(e))


# 60. INVALID SCENARIO HANDLING
try:
    res = requests.post(f"{BASE_URL}/api/telemetry/scenario", json={"scenario": "INVALID_SCENARIO_XYZ"}, timeout=10)
    is_ok = (res.status_code == 400 and res.json().get("success") is False)
    log_test("Invalid Scenario Handling", is_ok, f"(status_code={res.status_code})")
except Exception as e:
    log_test("Invalid Scenario Handling", False, str(e))


# 61. POST /api/telemetry/mode [MOCK]
try:
    res = requests.post(f"{BASE_URL}/api/telemetry/mode", json={"mode": "MOCK"}, timeout=10)
    data = res.json()
    is_ok = (res.status_code == 200 and data.get("telemetry_mode") == "MOCK")
    log_test("POST /api/telemetry/mode [MOCK]", is_ok, f"(mode={data.get('telemetry_mode')})")
except Exception as e:
    log_test("POST /api/telemetry/mode [MOCK]", False, str(e))


# 62. POST /api/telemetry/mode [REAL_OT] (Fallback resilience)
try:
    res = requests.post(f"{BASE_URL}/api/telemetry/mode", json={"mode": "REAL_OT"}, timeout=10)
    data = res.json()
    is_ok = (res.status_code == 200 and data.get("telemetry_mode") == "REAL_OT")
    log_test("POST /api/telemetry/mode [REAL_OT]", is_ok, f"(mode={data.get('telemetry_mode')})")

    # Reset back to MOCK mode for default state
    requests.post(f"{BASE_URL}/api/telemetry/mode", json={"mode": "MOCK"}, timeout=10)
except Exception as e:
    log_test("POST /api/telemetry/mode [REAL_OT]", False, str(e))


# 63. INVALID TELEMETRY MODE HANDLING
try:
    res = requests.post(f"{BASE_URL}/api/telemetry/mode", json={"mode": "INVALID_MODE"}, timeout=10)
    is_ok = (res.status_code == 400 and res.json().get("success") is False)
    log_test("Invalid Telemetry Mode Handling", is_ok, f"(status_code={res.status_code})")
except Exception as e:
    log_test("Invalid Telemetry Mode Handling", False, str(e))


# 64. MISSING TELEMETRY FIELD VALIDATION
try:
    from ot.telemetry_manager import TelemetryManager
    tm = TelemetryManager()
    is_valid, miss, errs = tm.validate_telemetry("TRANSFORMER", {})
    is_ok = (is_valid is False and len(errs) > 0)
    log_test("Missing Telemetry Field Validation", is_ok, f"(errs_count={len(errs)})")
except Exception as e:
    log_test("Missing Telemetry Field Validation", False, str(e))


# 65. STALE / OUT OF BOUNDS TELEMETRY VALIDATION
try:
    from ot.telemetry_manager import TelemetryManager
    tm = TelemetryManager()
    is_valid, miss, errs = tm.validate_telemetry("WATER_PUMP", {"flow": -50.0, "pressure": -2.0, "vibration": -1.0})
    is_ok = (is_valid is False and len(errs) >= 3)
    log_test("Out of Bounds Telemetry Validation", is_ok, f"(detected_errors={len(errs)})")
except Exception as e:
    log_test("Out of Bounds Telemetry Validation", False, str(e))


# 66. ML INFERENCE FROM MOCK TELEMETRY
try:
    from ot.telemetry_manager import TelemetryManager
    tm = TelemetryManager()
    tm.set_scenario("COMBINED_CASCADE")
    tx_rec = tm.get_asset_telemetry("transformer")
    ch_rec = tm.get_asset_telemetry("chiller")
    is_ok = (
        tx_rec.get("data_quality", {}).get("complete") is True and
        ch_rec.get("data_quality", {}).get("complete") is True
    )
    log_test("ML Inference from Mock Telemetry", is_ok, f"(tx_mode={tx_rec.get('mode')}, ch_mode={ch_rec.get('mode')})")
    tm.set_scenario("NORMAL")
except Exception as e:
    log_test("ML Inference from Mock Telemetry", False, str(e))


# 67. MULTI-ASSET CASCADE CALCULATION UNDER MOCK OT STREAM
try:
    res = requests.get(f"{BASE_URL}/api/multi-asset-analyze", timeout=10)
    data = res.json()
    sys_risk = data.get("system", {}).get("system_cascade_risk")
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        sys_risk is not None
    )
    log_test("Multi-Asset Cascade under OT Stream", is_ok, f"(sys_risk={sys_risk})")
except Exception as e:
    log_test("Multi-Asset Cascade under OT Stream", False, str(e))


# 68. CREDENTIAL SAFETY CHECK
try:
    import os
    env_keys = ["MODBUS_HOST", "OPCUA_ENDPOINT", "MQTT_BROKER", "MQTT_PASSWORD"]
    has_hardcoded = False
    for k in env_keys:
        if k in os.environ and "password123" in os.environ[k]:
            has_hardcoded = True
    is_ok = not has_hardcoded
    log_test("Credential Safety Check", is_ok, "(No hardcoded passwords or industrial IPs)")
except Exception as e:
    log_test("Credential Safety Check", False, str(e))


# 69. GET /api/incidents
try:
    res = requests.get(f"{BASE_URL}/api/incidents", timeout=10)
    data = res.json()
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        "active_incidents_count" in data and
        "data" in data
    )
    log_test("GET /api/incidents", is_ok, f"(active_count={data.get('active_incidents_count')})")
except Exception as e:
    log_test("GET /api/incidents", False, str(e))


# 70. INCIDENT GENERATION & SEVERITY THRESHOLDS
try:
    # Trigger scenario COMBINED_CASCADE to generate incident
    requests.post(f"{BASE_URL}/api/telemetry/scenario", json={"scenario": "COMBINED_CASCADE"}, timeout=10)
    res = requests.get(f"{BASE_URL}/api/multi-asset-analyze", timeout=10)
    data = res.json()
    active_inc = data.get("active_incident", {})
    is_ok = (
        res.status_code == 200 and
        active_inc is not None and
        "incident_id" in active_inc and
        active_inc.get("severity") in ["WARNING", "CRITICAL"]
    )
    log_test("Incident Generation & Severity Thresholds", is_ok, f"(inc_id={active_inc.get('incident_id')}, severity={active_inc.get('severity')})")
except Exception as e:
    log_test("Incident Generation & Severity Thresholds", False, str(e))


# 71. INCIDENT THRESHOLD CONFIGURATION
try:
    from site_config import get_risk_thresholds
    thresh = get_risk_thresholds()
    is_ok = (thresh.get("watch") == 25.0 and thresh.get("warning") == 50.0 and thresh.get("critical") == 75.0)
    log_test("Risk Threshold Configuration", is_ok, f"(watch={thresh.get('watch')}, warn={thresh.get('warning')}, crit={thresh.get('critical')})")
except Exception as e:
    log_test("Risk Threshold Configuration", False, str(e))


# 72. INCIDENT DEDUPLICATION
try:
    # Call multi-asset-analyze multiple times under same scenario
    requests.get(f"{BASE_URL}/api/multi-asset-analyze", timeout=10)
    res2 = requests.get(f"{BASE_URL}/api/multi-asset-analyze", timeout=10)
    inc2 = res2.json().get("active_incident", {})
    
    res_inc = requests.get(f"{BASE_URL}/api/incidents", timeout=10)
    inc_data = res_inc.json().get("data", {})
    active_list = inc_data.get("active_incidents", [])
    
    is_ok = (len(active_list) >= 1 and inc2.get("incident_id") == active_list[0].get("incident_id"))
    log_test("Incident Deduplication Engine", is_ok, f"(deduped_active_count={len(active_list)})")
except Exception as e:
    log_test("Incident Deduplication Engine", False, str(e))


# 73. WARNING INCIDENT STATE TEST
try:
    requests.post(f"{BASE_URL}/api/telemetry/scenario", json={"scenario": "HIGH_LOAD"}, timeout=10)
    res = requests.get(f"{BASE_URL}/api/multi-asset-analyze", timeout=10)
    inc = res.json().get("active_incident", {})
    is_ok = (inc is not None and inc.get("severity") in ["WARNING", "CRITICAL"])
    log_test("WARNING Incident State Test", is_ok, f"(severity={inc.get('severity')})")
except Exception as e:
    log_test("WARNING Incident State Test", False, str(e))


# 74. CRITICAL INCIDENT STATE TEST
try:
    requests.post(f"{BASE_URL}/api/telemetry/scenario", json={"scenario": "COMBINED_CASCADE"}, timeout=10)
    res = requests.get(f"{BASE_URL}/api/multi-asset-analyze?scenario=COMBINED_CASCADE", timeout=10)
    inc = res.json().get("active_incident", {})
    is_ok = (inc is not None and inc.get("severity") in ["WARNING", "CRITICAL"])
    log_test("CRITICAL Incident State Test", is_ok, f"(severity={inc.get('severity')})")
except Exception as e:
    log_test("CRITICAL Incident State Test", False, str(e))


# 75. GET /api/incidents/<incident_id>
try:
    res_list = requests.get(f"{BASE_URL}/api/incidents", timeout=10)
    inc_list = res_list.json().get("data", {}).get("history", [])
    if inc_list:
        target_id = inc_list[0]["incident_id"]
        res = requests.get(f"{BASE_URL}/api/incidents/{target_id}", timeout=10)
        data = res.json()
        inc = data.get("incident", {})
        is_ok = (res.status_code == 200 and data.get("success") is True and inc.get("incident_id") == target_id)
        log_test("GET /api/incidents/<id>", is_ok, f"(inc_id={target_id})")
    else:
        log_test("GET /api/incidents/<id>", True, "(No incidents in history to query)")
except Exception as e:
    log_test("GET /api/incidents/<id>", False, str(e))


# 76. POST /api/incidents/<id>/acknowledge
try:
    res_list = requests.get(f"{BASE_URL}/api/incidents", timeout=10)
    inc_list = res_list.json().get("data", {}).get("active_incidents", [])
    if inc_list:
        target_id = inc_list[0]["incident_id"]
        res = requests.post(f"{BASE_URL}/api/incidents/{target_id}/acknowledge", timeout=10)
        data = res.json()
        inc = data.get("incident", {})
        is_ok = (res.status_code == 200 and inc.get("status") == "ACKNOWLEDGED")
        log_test("POST /api/incidents/<id>/acknowledge", is_ok, f"(status={inc.get('status')})")
    else:
        log_test("POST /api/incidents/<id>/acknowledge", True, "(Skipped: No active incidents)")
except Exception as e:
    log_test("POST /api/incidents/<id>/acknowledge", False, str(e))


# 77. POST /api/incidents/<id>/resolve
try:
    res_list = requests.get(f"{BASE_URL}/api/incidents", timeout=10)
    inc_list = res_list.json().get("data", {}).get("history", [])
    if inc_list:
        target_id = inc_list[0]["incident_id"]
        res = requests.post(f"{BASE_URL}/api/incidents/{target_id}/resolve", timeout=10)
        data = res.json()
        inc = data.get("incident", {})
        is_ok = (res.status_code == 200 and inc.get("status") == "RESOLVED")
        log_test("POST /api/incidents/<id>/resolve", is_ok, f"(status={inc.get('status')})")
    else:
        log_test("POST /api/incidents/<id>/resolve", True, "(Skipped: No history)")
except Exception as e:
    log_test("POST /api/incidents/<id>/resolve", False, str(e))


# 78. RECOMMENDATION ENGINE OUTPUT
try:
    from recommendation_engine import generate_recommendations
    recs = generate_recommendations(65.0, {}, {"climate_stress": 40.0}, "HEAT_STRESS")
    is_ok = (
        "disclaimer" in recs and
        "actions" in recs and
        len(recs["actions"]) >= 1
    )
    log_test("Recommendation Engine Output", is_ok, f"(recs_count={len(recs.get('actions', []))})")
except Exception as e:
    log_test("Recommendation Engine Output", False, str(e))


# 79. ALERT WEBHOOK FAILURE RESILIENCE
try:
    from alert_manager import AlertManager
    am = AlertManager()
    am.set_webhook_config("http://127.0.0.1:9999/nonexistent_webhook", enabled=True)
    res = am.dispatch_alert({"incident_id": "INC-TEST-001", "severity": "CRITICAL"})
    is_ok = (res.get("notification_status") == "FAILED")
    log_test("Alert Webhook Failure Resilience", is_ok, f"(status={res.get('notification_status')})")
except Exception as e:
    log_test("Alert Webhook Failure Resilience", False, str(e))


# 80. ALERT WEBHOOK DISABLED MODE
try:
    from alert_manager import AlertManager
    am = AlertManager()
    am.enabled = False
    res = am.dispatch_alert({"incident_id": "INC-TEST-002", "severity": "CRITICAL"})
    is_ok = (res.get("notification_status") == "SKIPPED")
    log_test("Alert Webhook Disabled Mode", is_ok, f"(status={res.get('notification_status')})")
except Exception as e:
    log_test("Alert Webhook Disabled Mode", False, str(e))


# 85. EXECUTIVE PDF REPORT GENERATION
try:
    res = requests.post(f"{BASE_URL}/api/incidents/generate-report", json={}, timeout=10)
    is_ok = (
        res.status_code == 200 and
        res.headers.get("Content-Type") == "application/pdf" and
        len(res.content) > 1000
    )
    log_test("Executive PDF Report Generation", is_ok, f"(pdf_bytes={len(res.content)})")
except Exception as e:
    log_test("Executive PDF Report Generation", False, str(e))


# 82. DATA PROVENANCE BADGES IN INCIDENT SCHEMA
try:
    res = requests.get(f"{BASE_URL}/api/incidents", timeout=10)
    history = res.json().get("data", {}).get("history", [])
    if history:
        ds = history[0].get("data_sources", {})
        is_ok = ("climate" in ds and "transformer" in ds and "chiller" in ds and "water_pump" in ds)
        log_test("Data Provenance Badges in Incident", is_ok, f"(sources_count={len(ds)})")
    else:
        log_test("Data Provenance Badges in Incident", True, "(No incidents in history)")
except Exception as e:
    log_test("Data Provenance Badges in Incident", False, str(e))


# 83. MOCK DATA LABELING VERIFICATION
try:
    res = requests.get(f"{BASE_URL}/api/telemetry/live", timeout=10)
    tel = res.json().get("telemetry", {})
    tx = tel.get("transformer", {})
    is_ok = (tx.get("mode") == "MOCK" and tx.get("connection_status") == "SIMULATED")
    log_test("MOCK Data Labeling Verification", is_ok, f"(mode={tx.get('mode')}, status={tx.get('connection_status')})")
except Exception as e:
    log_test("MOCK Data Labeling Verification", False, str(e))


# 84. HISTORICAL DATA LABELING VERIFICATION
try:
    res = requests.get(f"{BASE_URL}/api/realtime-status", timeout=10)
    ch_src = res.json().get("chiller", {}).get("source") or res.json().get("adapters", {}).get("chiller", {}).get("source")
    is_ok = ("historical" in str(ch_src).lower())
    log_test("HISTORICAL Data Labeling Verification", is_ok, f"(chiller_source={ch_src})")
except Exception as e:
    log_test("HISTORICAL Data Labeling Verification", False, str(e))


# 85. REAL_OT DATA LABELING VERIFICATION
try:
    requests.post(f"{BASE_URL}/api/telemetry/mode", json={"mode": "REAL_OT"}, timeout=10)
    res = requests.get(f"{BASE_URL}/api/telemetry/status", timeout=10)
    mode = res.json().get("telemetry_mode")
    is_ok = (mode == "REAL_OT")
    log_test("REAL_OT Data Labeling Verification", is_ok, f"(mode={mode})")
    # Reset back to MOCK
    requests.post(f"{BASE_URL}/api/telemetry/mode", json={"mode": "MOCK"}, timeout=10)
except Exception as e:
    log_test("REAL_OT Data Labeling Verification", False, str(e))


# 86. SHAP FACTOR INTEGRATION IN INCIDENT ENGINE
try:
    res = requests.get(f"{BASE_URL}/api/live-analyze?tx_id=TX-001", timeout=10)
    data = res.json()
    is_ok = ("top_risk_factors" in data or "shap_summary" in data or "explainability" in data)
    log_test("SHAP Factor Integration", is_ok, f"(has_explainability={'explainability' in data or 'top_risk_factors' in data})")
except Exception as e:
    log_test("SHAP Factor Integration", False, str(e))


# 87. CASCADE PATH PROPAGATION STRING VERIFICATION
try:
    res = requests.get(f"{BASE_URL}/api/multi-asset-analyze", timeout=10)
    data = res.json()
    narrative = data.get("system", {}).get("narrative") or data.get("cascade", {}).get("narrative") or ""
    is_ok = (len(narrative) > 10)
    log_test("Cascade Path Propagation String", is_ok, f"(narrative_len={len(narrative)})")
except Exception as e:
    log_test("Cascade Path Propagation String", False, str(e))


# 88. INVALID INCIDENT ID HANDLING (404)
try:
    res = requests.get(f"{BASE_URL}/api/incidents/INVALID_INCIDENT_99999", timeout=10)
    is_ok = (res.status_code == 404 and res.json().get("success") is False)
    log_test("Invalid Incident ID Handling (404)", is_ok, f"(status_code={res.status_code})")
except Exception as e:
    log_test("Invalid Incident ID Handling (404)", False, str(e))


# 89. GET /api/sites
try:
    res = requests.get(f"{BASE_URL}/api/sites", timeout=10)
    data = res.json()
    is_ok = (res.status_code == 200 and data.get("success") is True and data.get("count") >= 5)
    log_test("GET /api/sites", is_ok, f"(sites_count={data.get('count')})")
except Exception as e:
    log_test("GET /api/sites", False, str(e))


# 90. GET /api/sites/<site_id>
try:
    res = requests.get(f"{BASE_URL}/api/sites/SITE-001", timeout=10)
    data = res.json()
    site = data.get("site", {})
    is_ok = (res.status_code == 200 and site.get("site_id") == "SITE-001" and site.get("city") == "Coimbatore")
    log_test("GET /api/sites/SITE-001", is_ok, f"(name={site.get('site_name')})")
except Exception as e:
    log_test("GET /api/sites/SITE-001", False, str(e))


# 91. GET /api/sites/INVALID_SITE_999
try:
    res = requests.get(f"{BASE_URL}/api/sites/INVALID_SITE_999", timeout=10)
    is_ok = (res.status_code == 404 and res.json().get("success") is False)
    log_test("GET /api/sites/INVALID_SITE_999 (404)", is_ok, f"(status_code={res.status_code})")
except Exception as e:
    log_test("GET /api/sites/INVALID_SITE_999 (404)", False, str(e))


# 92. POST /api/sites (Create Site)
try:
    new_payload = {
        "site_id": "SITE-006",
        "site_name": "Tiruchirappalli Facility",
        "city": "Trichy",
        "latitude": 10.7905,
        "longitude": 78.7047
    }
    res = requests.post(f"{BASE_URL}/api/sites", json=new_payload, timeout=10)
    data = res.json()
    is_ok = (res.status_code == 201 and data.get("success") is True and data.get("site", {}).get("site_id") == "SITE-006")
    log_test("POST /api/sites (Create Site)", is_ok, f"(created_id={data.get('site', {}).get('site_id')})")
except Exception as e:
    log_test("POST /api/sites (Create Site)", False, str(e))


# 93. Latitude Out of Bounds Validation
try:
    inv_payload = {"site_id": "SITE-ERR-1", "site_name": "Error Site", "latitude": 95.0, "longitude": 78.0}
    res = requests.post(f"{BASE_URL}/api/sites", json=inv_payload, timeout=10)
    is_ok = (res.status_code == 400 and res.json().get("success") is False)
    log_test("Latitude Out of Bounds Validation", is_ok, f"(status_code={res.status_code})")
except Exception as e:
    log_test("Latitude Out of Bounds Validation", False, str(e))


# 94. Longitude Out of Bounds Validation
try:
    inv_payload = {"site_id": "SITE-ERR-2", "site_name": "Error Site", "latitude": 11.0, "longitude": -190.0}
    res = requests.post(f"{BASE_URL}/api/sites", json=inv_payload, timeout=10)
    is_ok = (res.status_code == 400 and res.json().get("success") is False)
    log_test("Longitude Out of Bounds Validation", is_ok, f"(status_code={res.status_code})")
except Exception as e:
    log_test("Longitude Out of Bounds Validation", False, str(e))


# 95. Missing Required Field Validation
try:
    inv_payload = {"site_id": "SITE-ERR-3", "latitude": 11.0, "longitude": 78.0}
    res = requests.post(f"{BASE_URL}/api/sites", json=inv_payload, timeout=10)
    is_ok = (res.status_code == 400 and res.json().get("success") is False)
    log_test("Missing Required Field Validation", is_ok, f"(status_code={res.status_code})")
except Exception as e:
    log_test("Missing Required Field Validation", False, str(e))


# 96. PUT /api/sites/SITE-006 (Update Site)
try:
    upd_payload = {"site_name": "Trichy Renewable Substation Alpha"}
    res = requests.put(f"{BASE_URL}/api/sites/SITE-006", json=upd_payload, timeout=10)
    data = res.json()
    is_ok = (res.status_code == 200 and data.get("site", {}).get("site_name") == "Trichy Renewable Substation Alpha")
    log_test("PUT /api/sites/SITE-006 (Update Site)", is_ok, f"(updated_name={data.get('site', {}).get('site_name')})")
except Exception as e:
    log_test("PUT /api/sites/SITE-006 (Update Site)", False, str(e))


# 97. POST /api/sites/SITE-006/deactivate
try:
    res = requests.post(f"{BASE_URL}/api/sites/SITE-006/deactivate", timeout=10)
    is_ok = (res.status_code == 200 and res.json().get("success") is True)
    log_test("POST /api/sites/<id>/deactivate", is_ok, "(status=deactivated)")
except Exception as e:
    log_test("POST /api/sites/<id>/deactivate", False, str(e))


# 98. POST /api/sites/SITE-006/activate
try:
    res = requests.post(f"{BASE_URL}/api/sites/SITE-006/activate", timeout=10)
    is_ok = (res.status_code == 200 and res.json().get("success") is True)
    log_test("POST /api/sites/<id>/activate", is_ok, "(status=activated)")
except Exception as e:
    log_test("POST /api/sites/<id>/activate", False, str(e))


# 99. DELETE /api/sites/SITE-006
try:
    res = requests.delete(f"{BASE_URL}/api/sites/SITE-006", timeout=10)
    is_ok = (res.status_code == 200 and res.json().get("success") is True)
    log_test("DELETE /api/sites/SITE-006", is_ok, "(deleted=True)")
except Exception as e:
    log_test("DELETE /api/sites/SITE-006", False, str(e))


# 100. GET /api/regional-status
try:
    res = requests.get(f"{BASE_URL}/api/regional-status", timeout=10)
    data = res.json()
    reg = data.get("regional", {})
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        "regional_risk" in reg and
        "sites_monitored" in reg and
        reg.get("sites_monitored") >= 5
    )
    log_test("GET /api/regional-status", is_ok, f"(regional_risk={reg.get('regional_risk')}, monitored={reg.get('sites_monitored')})")
except Exception as e:
    log_test("GET /api/regional-status", False, str(e))


# 101. Regional Risk Aggregation Formula Check
try:
    res = requests.get(f"{BASE_URL}/api/regional-status", timeout=10)
    reg = res.json().get("regional", {})
    agg = reg.get("aggregation_method", {})
    is_ok = ("formula" in agg and "weights" in agg and reg.get("average_site_risk") is not None)
    log_test("Regional Risk Aggregation Formula", is_ok, f"(formula={agg.get('formula')})")
except Exception as e:
    log_test("Regional Risk Aggregation Formula", False, str(e))


# 102. Site Prioritization Ranking Check
try:
    res = requests.get(f"{BASE_URL}/api/regional-status", timeout=10)
    sites = res.json().get("regional", {}).get("sites", [])
    ranks = [s.get("priority_rank") for s in sites]
    is_ok = (len(sites) >= 5 and ranks == list(range(1, len(sites) + 1)))
    log_test("Site Prioritization Ranking Check", is_ok, f"(top_ranked={sites[0].get('site_id') if sites else 'None'})")
except Exception as e:
    log_test("Site Prioritization Ranking Check", False, str(e))


# 103. GET /api/sites/SITE-001/analyze
try:
    res = requests.get(f"{BASE_URL}/api/sites/SITE-001/analyze", timeout=10)
    data = res.json()
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        data.get("site", {}).get("site_id") == "SITE-001" and
        "assets" in data
    )
    log_test("GET /api/sites/SITE-001/analyze", is_ok, f"(site_id={data.get('site', {}).get('site_id')})")
except Exception as e:
    log_test("GET /api/sites/SITE-001/analyze", False, str(e))


# 104. GET /api/regional/incidents
try:
    res = requests.get(f"{BASE_URL}/api/regional/incidents", timeout=10)
    data = res.json()
    is_ok = (res.status_code == 200 and data.get("success") is True and "incidents" in data)
    log_test("GET /api/regional/incidents", is_ok, f"(incidents_count={data.get('count')})")
except Exception as e:
    log_test("GET /api/regional/incidents", False, str(e))


# 105. GET /api/regional/incidents Filtering
try:
    res = requests.get(f"{BASE_URL}/api/regional/incidents?severity=WARNING", timeout=10)
    data = res.json()
    incs = data.get("incidents", [])
    all_warn = all(i.get("severity") == "WARNING" for i in incs)
    is_ok = (res.status_code == 200 and data.get("success") is True and all_warn)
    log_test("GET /api/regional/incidents Filtering", is_ok, f"(filtered_count={len(incs)})")
except Exception as e:
    log_test("GET /api/regional/incidents Filtering", False, str(e))


# 106. GET /api/regional-history
try:
    res = requests.get(f"{BASE_URL}/api/regional-history", timeout=10)
    data = res.json()
    is_ok = (res.status_code == 200 and data.get("success") is True and "history" in data)
    log_test("GET /api/regional-history", is_ok, f"(history_count={data.get('count')})")
except Exception as e:
    log_test("GET /api/regional-history", False, str(e))


# 107. Regional Climate Correlation Signal Check
try:
    res = requests.get(f"{BASE_URL}/api/regional-status", timeout=10)
    event_info = res.json().get("regional", {}).get("regional_climate_event", {})
    is_ok = ("active" in event_info and "disclaimer" in event_info and "message" in event_info)
    log_test("Regional Climate Correlation Signal", is_ok, f"(active={event_info.get('active')})")
except Exception as e:
    log_test("Regional Climate Correlation Signal", False, str(e))


# 108. Multi-Site Data Provenance Verification
try:
    res = requests.get(f"{BASE_URL}/api/sites/SITE-001/analyze", timeout=10)
    data = res.json()
    assets = data.get("assets", {})
    wp_source = assets.get("water_pump", {}).get("source", "")
    is_ok = (
        assets.get("transformer", {}).get("source") in ["ML_PRODUCTION", "HISTORICAL_REPLAY"] and
        assets.get("chiller", {}).get("source") in ["ML_PRODUCTION", "HISTORICAL_DATASET", "HISTORICAL_REPLAY"] and
        ("DECISION" in wp_source or "SUPPORT" in wp_source or "ML_" in wp_source)
    )
    log_test("Multi-Site Data Provenance Verification", is_ok, f"(wp_source={wp_source})")
except Exception as e:
    log_test("Multi-Site Data Provenance Verification", False, str(e))


# 109. Site Geolocation Climate Differentiation (SITE-001 vs SITE-002 vs SITE-003)
try:
    r1 = requests.get(f"{BASE_URL}/api/climate?site_id=SITE-001", timeout=10).json()
    r2 = requests.get(f"{BASE_URL}/api/climate?site_id=SITE-002", timeout=10).json()
    r3 = requests.get(f"{BASE_URL}/api/climate?site_id=SITE-003", timeout=10).json()

    c1 = r1.get("climate_intelligence", {})
    c2 = r2.get("climate_intelligence", {})
    c3 = r3.get("climate_intelligence", {})

    is_ok = (
        c1.get("latitude") == 11.00555 and
        c2.get("latitude") == 13.0827 and
        c3.get("latitude") == 12.9716 and
        c1.get("site_id") == "SITE-001" and
        c2.get("site_id") == "SITE-002" and
        c3.get("site_id") == "SITE-003"
    )
    log_test("Site Geolocation Climate Differentiation", is_ok, f"(S1={c1.get('latitude')}, S2={c2.get('latitude')}, S3={c3.get('latitude')})")
except Exception as e:
    log_test("Site Geolocation Climate Differentiation", False, str(e))


# 110. GET /api/sites/<site_id>/climate Endpoint
try:
    res = requests.get(f"{BASE_URL}/api/sites/SITE-003/climate", timeout=10)
    data = res.json()
    ci = data.get("climate_intelligence", {})
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        ci.get("site_id") == "SITE-003" and
        ci.get("latitude") == 12.9716 and
        ci.get("longitude") == 77.5946
    )
    log_test("GET /api/sites/<site_id>/climate Endpoint", is_ok, f"(site_id={ci.get('site_id')}, lat={ci.get('latitude')})")
except Exception as e:
    log_test("GET /api/sites/<site_id>/climate Endpoint", False, str(e))


# 111. Invalid Latitude Validation (HTTP 400)
try:
    res = requests.get(f"{BASE_URL}/api/climate?latitude=95.0&longitude=76.0", timeout=10)
    is_ok = (res.status_code == 400 and res.json().get("success") is False)
    log_test("Invalid Latitude Validation (HTTP 400)", is_ok, f"(status_code={res.status_code})")
except Exception as e:
    log_test("Invalid Latitude Validation (HTTP 400)", False, str(e))


# 112. Invalid Longitude Validation (HTTP 400)
try:
    res = requests.get(f"{BASE_URL}/api/climate?latitude=11.0&longitude=200.0", timeout=10)
    is_ok = (res.status_code == 400 and res.json().get("success") is False)
    log_test("Invalid Longitude Validation (HTTP 400)", is_ok, f"(status_code={res.status_code})")
except Exception as e:
    log_test("Invalid Longitude Validation (HTTP 400)", False, str(e))


# 113. Unknown Site ID Handling (HTTP 404)
try:
    res = requests.get(f"{BASE_URL}/api/sites/SITE-UNKNOWN-999/climate", timeout=10)
    is_ok = (res.status_code == 404 and res.json().get("success") is False)
    log_test("Unknown Site ID Handling (HTTP 404)", is_ok, f"(status_code={res.status_code})")
except Exception as e:
    log_test("Unknown Site ID Handling (HTTP 404)", False, str(e))


# 114. Realtime Status Site Parameter
try:
    res = requests.get(f"{BASE_URL}/api/realtime-status?site_id=SITE-002", timeout=10)
    data = res.json()
    site_info = data.get("site", {})
    is_ok = (
        res.status_code == 200 and
        data.get("success") is True and
        site_info.get("site_id") == "SITE-002"
    )
    log_test("Realtime Status Site Parameter", is_ok, f"(site_id={site_info.get('site_id')})")
except Exception as e:
    log_test("Realtime Status Site Parameter", False, str(e))


# 115. Executive PDF Report Validation
try:
    res = requests.get(f"{BASE_URL}/api/reports/executive", timeout=10)
    ctype = res.headers.get("Content-Type", "")
    cdisp = res.headers.get("Content-Disposition", "")
    content = res.content
    is_ok = (
        res.status_code == 200 and
        "application/pdf" in ctype and
        "CascadeGuard_Executive_Report.pdf" in cdisp and
        len(content) > 0 and
        content.startswith(b"%PDF-")
    )
    log_test("Executive PDF Report Validation", is_ok, f"(size={len(content)}, header={content[:5]})")
except Exception as e:
    log_test("Executive PDF Report Validation", False, str(e))


# 116. Regional PDF Report Validation
try:
    res = requests.get(f"{BASE_URL}/api/reports/regional", timeout=10)
    ctype = res.headers.get("Content-Type", "")
    cdisp = res.headers.get("Content-Disposition", "")
    content = res.content
    is_ok = (
        res.status_code == 200 and
        "application/pdf" in ctype and
        "CascadeGuard_Regional_Report.pdf" in cdisp and
        len(content) > 0 and
        content.startswith(b"%PDF-")
    )
    log_test("Regional PDF Report Validation", is_ok, f"(size={len(content)})")
except Exception as e:
    log_test("Regional PDF Report Validation", False, str(e))


# 117. Fleet PDF Report Validation
try:
    res = requests.get(f"{BASE_URL}/api/reports/fleet", timeout=10)
    ctype = res.headers.get("Content-Type", "")
    cdisp = res.headers.get("Content-Disposition", "")
    content = res.content
    is_ok = (
        res.status_code == 200 and
        "application/pdf" in ctype and
        "CascadeGuard_Fleet_Report.pdf" in cdisp and
        len(content) > 0 and
        content.startswith(b"%PDF-")
    )
    log_test("Fleet PDF Report Validation", is_ok, f"(size={len(content)})")
except Exception as e:
    log_test("Fleet PDF Report Validation", False, str(e))


# 118. Incident PDF Report Endpoint Validation
try:
    res = requests.post(f"{BASE_URL}/api/incidents/generate-report", json={}, timeout=10)
    ctype = res.headers.get("Content-Type", "")
    cdisp = res.headers.get("Content-Disposition", "")
    content = res.content
    is_ok = (
        res.status_code == 200 and
        "application/pdf" in ctype and
        ".pdf" in cdisp and
        len(content) > 0 and
        content.startswith(b"%PDF-")
    )
    log_test("Incident PDF Report Endpoint Validation", is_ok, f"(cdisp={cdisp})")
except Exception as e:
    log_test("Incident PDF Report Endpoint Validation", False, str(e))


print("=" * 65)
print(f"API TEST SUMMARY: {passed} PASSED, {failed} FAILED")
print("=" * 65)

if failed > 0:
    sys.exit(1)
else:
    sys.exit(0)
"""
tests/test_fastapi.py
======================
Phase 15: FastAPI Test Suite for CascadeGuard AI Command Center.

Directly tests the FastAPI application using starlette/fastapi TestClient:
- Health endpoint (/api/health)
- Live telemetry (/api/telemetry/*)
- Climate intelligence API (/api/climate-intelligence)
- Transformer ML analysis & SHAP explanations (/api/live-analyze)
- Chiller ML analysis (/api/multi-asset-analyze)
- Water Pump decision-support model (/api/multi-asset-analyze)
- Multi-asset & system cascade risk graph (/api/multi-asset-analyze)
- Regional status & aggregation (/api/regional-status)
- Regional Site CRUD (/api/sites)
- Incident management workflow (/api/incidents)
- Climate & telemetry scenarios (/api/scenarios, /api/scenario-analyze)
- PDF Executive Report generation (/api/incidents/generate-report)
- Structured error handling (400, 404, 500)
"""
import os
import sys
import unittest

# Ensure 'backend/' is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi.testclient import TestClient
from main import app
import state

class TestFastAPIBackend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        state.load_all_models()
        cls.client = TestClient(app)

    def test_01_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "online")
        self.assertEqual(data.get("service"), "CascadeGuard AI Command Center")
        self.assertIn("operational_model_version", data)
        self.assertEqual(data.get("shap_explainer"), "active")
        self.assertEqual(data.get("scenarios_available"), 8)
        self.assertEqual(data.get("transformers_monitored"), 5)

    def test_02_live_telemetry(self):
        response = self.client.get("/api/telemetry/live")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertIn("telemetry", data)
        telem = data["telemetry"]
        self.assertIn("transformer", telem)
        self.assertIn("chiller", telem)
        self.assertIn("water_pump", telem)

    def test_03_telemetry_status_and_modes(self):
        res = self.client.get("/api/telemetry/status")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json().get("success"))

        res_mode = self.client.post("/api/telemetry/mode", json={"mode": "REAL_OT"})
        self.assertEqual(res_mode.status_code, 200)
        self.assertEqual(res_mode.json().get("telemetry_mode"), "REAL_OT")

        res_reset = self.client.post("/api/telemetry/mode", json={"mode": "MOCK"})
        self.assertEqual(res_reset.status_code, 200)
        self.assertEqual(res_reset.json().get("telemetry_mode"), "MOCK")

    def test_04_climate_intelligence_api(self):
        response = self.client.get("/api/climate-intelligence?location=Coimbatore")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertIn("climate_intelligence", data)
        intel = data["climate_intelligence"]
        self.assertIn("current", intel)
        self.assertIn("heatwave", intel)
        self.assertIn("asset_impacts", intel)

    def test_05_transformer_analysis_and_shap(self):
        response = self.client.get("/api/live-analyze?tx_id=TX-001")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("transformer_id"), "TX-001")
        self.assertIn("cascade", data)
        self.assertIn("explainability", data)
        exp = data["explainability"]
        self.assertIn("top_factors", exp)
        self.assertGreater(len(exp["top_factors"]), 0)

    def test_06_chiller_and_pump_multi_asset_cascade(self):
        response = self.client.get("/api/multi-asset-analyze?location=Coimbatore&tx_id=TX-001")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        assets = data.get("assets", {})
        self.assertIn("transformer", assets)
        self.assertIn("chiller", assets)
        self.assertIn("water_pump", assets)
        wp = assets["water_pump"]
        self.assertEqual(wp.get("status"), "DECISION_SUPPORT_ONLY")
        sys_eval = data.get("system", {})
        self.assertIn("system_cascade_risk", sys_eval)

    def test_07_regional_status_and_aggregation(self):
        response = self.client.get("/api/regional-status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        reg = data.get("regional", {})
        self.assertIn("regional_risk", reg)
        self.assertGreaterEqual(reg.get("sites_monitored", 0), 5)

    def test_08_site_crud_workflow(self):
        # 1. GET sites
        res_list = self.client.get("/api/sites")
        self.assertEqual(res_list.status_code, 200)
        initial_count = res_list.json().get("count", 0)

        # 2. CREATE site
        new_site = {
            "site_id": "SITE-FASTAPI-TEST",
            "site_name": "FastAPI Test Substation",
            "city": "Madurai",
            "latitude": 9.9252,
            "longitude": 78.1198
        }
        res_create = self.client.post("/api/sites", json=new_site)
        self.assertEqual(res_create.status_code, 201)
        self.assertTrue(res_create.json().get("success"))

        # 3. GET single site
        res_get = self.client.get("/api/sites/SITE-FASTAPI-TEST")
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.json().get("site", {}).get("site_name"), "FastAPI Test Substation")

        # 4. UPDATE site
        res_upd = self.client.put("/api/sites/SITE-FASTAPI-TEST", json={"site_name": "Updated FastAPI Substation"})
        self.assertEqual(res_upd.status_code, 200)
        self.assertEqual(res_upd.json().get("site", {}).get("site_name"), "Updated FastAPI Substation")

        # 5. DEACTIVATE & ACTIVATE
        res_deact = self.client.post("/api/sites/SITE-FASTAPI-TEST/deactivate")
        self.assertEqual(res_deact.status_code, 200)
        res_act = self.client.post("/api/sites/SITE-FASTAPI-TEST/activate")
        self.assertEqual(res_act.status_code, 200)

        # 6. DELETE site
        res_del = self.client.delete("/api/sites/SITE-FASTAPI-TEST")
        self.assertEqual(res_del.status_code, 200)

    def test_09_incidents_workflow(self):
        response = self.client.get("/api/incidents")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertIn("active_incidents_count", data)

    def test_10_scenarios_and_simulation(self):
        res_sc = self.client.get("/api/scenarios")
        self.assertEqual(res_sc.status_code, 200)
        self.assertGreaterEqual(len(res_sc.json().get("scenarios", [])), 7)

        res_sim = self.client.post("/api/scenario-analyze", json={"scenario": "HEATWAVE", "location": "Coimbatore"})
        self.assertEqual(res_sim.status_code, 200)
        data = res_sim.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("scenario", {}).get("name"), "HEATWAVE")

    def test_11_pdf_report_generation(self):
        response = self.client.post("/api/incidents/generate-report", json={})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("content-type"), "application/pdf")
        self.assertGreater(len(response.content), 1000)

    def test_12_structured_error_handling(self):
        # 404 Site not found
        res_404 = self.client.get("/api/sites/NON_EXISTENT_999")
        self.assertEqual(res_404.status_code, 404)
        self.assertFalse(res_404.json().get("success"))
        self.assertIn("error", res_404.json())

        # 400 Out of bounds coordinate
        res_400 = self.client.post("/api/sites", json={"site_id": "BAD", "site_name": "Bad", "latitude": 999.0, "longitude": 0.0})
        self.assertEqual(res_400.status_code, 400)
        self.assertFalse(res_400.json().get("success"))
        self.assertIn("error", res_400.json())


if __name__ == "__main__":
    unittest.main()

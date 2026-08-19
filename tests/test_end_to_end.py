"""
tests/test_end_to_end.py
========================
Comprehensive End-to-End Test Suite for CascadeGuard Platform (Phase I)

Tests complete pipeline without requiring frontend:
Weather -> Features -> Load Model -> Transformer Model -> Chiller Model -> Pump Model -> Flood Model -> Cascade Risk -> Recommendation Engine -> Model Health
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi.testclient import TestClient
from main import app
from services.cascade_service import evaluate_cascade_risk
from services.recommendation_service import generate_recommendations
from services.model_health_service import get_model_health_report

class TestCascadeGuardEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_step_1_weather_normalization(self):
        res = self.client.get("/api/weather")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("facility", {}).get("name"), "KMCH")
        self.assertEqual(data.get("facility", {}).get("city"), "Coimbatore")
        self.assertIn("current", data)

    def test_step_2_hospital_load_model(self):
        res = self.client.get("/api/predictions/load")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("model_id"), "Model-1-HospitalLoad")
        self.assertIn("prediction", data)
        self.assertIn("P1_critical_kw", data["prediction"]["medical_tiers"])

    def test_step_3_transformer_thermal_model(self):
        res = self.client.get("/api/predictions/transformer")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("model_id"), "Model-2-TransformerThermal")
        self.assertIn("predicted_oti_degc", data["prediction"])

    def test_step_4_chiller_fault_model(self):
        res = self.client.get("/api/predictions/chiller")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("model_id"), "Model-4-ChillerFault")
        self.assertIn("predicted_class_name", data["prediction"])

    def test_step_5_water_pump_decision_support_model(self):
        res = self.client.get("/api/predictions/pump")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("model_id"), "Model-5-WaterPumpRisk")
        self.assertEqual(data.get("status"), "DECISION_SUPPORT_ONLY")
        self.assertIn("DECISION SUPPORT ONLY", data["prediction"]["model_reliability"])

    def test_step_6_flood_exposure_model(self):
        res = self.client.get("/api/predictions/flood")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("model_id"), "Model-6-FloodRisk")
        self.assertIn("flood_risk_label", data["prediction"])

    def test_step_7_cascade_risk_engine(self):
        res = self.client.get("/api/cascade/current")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertIn("overall_risk", data)
        self.assertIn("explanation", data)
        exp = data["explanation"]
        self.assertIn("why", exp)
        self.assertIn("what", exp)
        self.assertIn("when", exp)
        self.assertIn("impact", exp)

    def test_step_8_recommendation_engine(self):
        res = self.client.get("/api/recommendations")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        recs = data.get("recommendations", {})
        self.assertIn("actions", recs)
        for act in recs["actions"]:
            self.assertTrue(act.get("requires_human_approval"))

    def test_step_9_model_health_service(self):
        report = get_model_health_report()
        self.assertEqual(len(report), 6)
        pump_model = next(m for m in report if m["model_id"] == "model_5" or "Water Pump" in m["model_name"])
        self.assertEqual(pump_model["status"], "DECISION_SUPPORT_ONLY")

if __name__ == "__main__":
    unittest.main()

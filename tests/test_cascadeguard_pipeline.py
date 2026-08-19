"""
tests/test_cascadeguard_pipeline.py
====================================
End-to-End Pipeline Verification Test Suite for CascadeGuard Platform
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi.testclient import TestClient
from main import app

class TestCascadeGuardPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_weather_api(self):
        response = self.client.get("/api/weather")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("facility", {}).get("name"), "KMCH")
        self.assertEqual(data.get("facility", {}).get("city"), "Coimbatore")
        self.assertEqual(data.get("source"), "Open-Meteo")
        self.assertIn("current", data)
        self.assertIn("forecast", data)

    def test_02_load_prediction_api(self):
        response = self.client.get("/api/predictions/load")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertIn("load_forecasting", data)

    def test_03_transformer_prediction_api(self):
        response = self.client.get("/api/predictions/transformer")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("equipment_id"), "T1")

    def test_04_chiller_prediction_api(self):
        response = self.client.get("/api/predictions/chiller")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("equipment_id"), "C1")

    def test_05_pump_prediction_api(self):
        response = self.client.get("/api/predictions/pump")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("equipment_id"), "P1")

    def test_06_cascade_risk_api(self):
        response = self.client.get("/api/risk/cascade")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        cascade = data.get("cascade_risk", {})
        self.assertIn("overall_risk", cascade)
        self.assertIn("level", cascade)

    def test_07_recommendations_api(self):
        response = self.client.get("/api/recommendations")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        recs = data.get("recommendations", {})
        self.assertIn("actions", recs)
        self.assertIn("ai_explanation", recs)

    def test_08_simulation_api(self):
        response = self.client.post("/api/simulation/run?scenario_key=HEATWAVE")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        sim = data.get("simulation", {})
        self.assertEqual(sim.get("data_type"), "SIMULATION")
        self.assertEqual(sim.get("scenario_key"), "HEATWAVE")

if __name__ == "__main__":
    unittest.main()

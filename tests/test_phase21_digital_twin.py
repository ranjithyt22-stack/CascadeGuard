"""
tests/test_phase21_digital_twin.py
===================================
Phase 21 Automated Test Suite: Interactive Digital Twin & Manual What-If Climate Simulator

Tests physics-based Digital Twin simulation, duration stress accumulation, equipment failure toggles,
Climate Resilience Score, primary risk driver identification, intervention strategy comparison, and honest ML integration.
"""

import sys
import unittest
from pathlib import Path

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import state
from site_registry import SiteRegistry
from api_clients.weather_client import WeatherAPIClient
from services.digital_twin_engine import DigitalTwinEngine


class TestPhase21DigitalTwin(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not hasattr(state, "site_registry") or state.site_registry is None:
            state.site_registry = SiteRegistry()
        if not hasattr(state, "weather_client_inst") or state.weather_client_inst is None:
            state.weather_client_inst = WeatherAPIClient()

    def setUp(self):
        self.engine = DigitalTwinEngine()

    def test_apparent_temperature_and_resilience_classification(self):
        app_t = self.engine.calculate_apparent_temperature(40.0, 80.0, 10.0)
        self.assertGreater(app_t, 40.0)

        self.assertEqual(self.engine.calculate_resilience_classification(85.0), "HIGH RESILIENCE")
        self.assertEqual(self.engine.calculate_resilience_classification(65.0), "GOOD RESILIENCE")
        self.assertEqual(self.engine.calculate_resilience_classification(45.0), "VULNERABLE")
        self.assertEqual(self.engine.calculate_resilience_classification(25.0), "HIGHLY VULNERABLE")
        self.assertEqual(self.engine.calculate_resilience_classification(10.0), "CRITICAL")

    def test_digital_twin_simulation_and_cascade_path(self):
        inputs = {
            "temperature": 42.5,
            "humidity": 85.0,
            "rainfall": 15.0,
            "duration_hours": 8.0,
            "transformer_load": 92.0,
            "transformer_cooling": 80.0,
            "chiller_capacity": 70.0,
            "pump_flow": 85.0
        }
        res = self.engine.simulate_digital_twin("SITE-001", inputs)
        self.assertTrue(res["success"])
        self.assertEqual(res["simulation_mode"], "DIGITAL_TWIN")
        self.assertIn("baseline", res)
        self.assertIn("scenario", res)
        self.assertIn("resilience_score", res["scenario"])
        self.assertIn("equipment", res)
        self.assertIn("cascade_path", res)
        self.assertEqual(len(res["cascade_path"]), 5)

    def test_duration_stress_accumulation(self):
        short_inputs = {"temperature": 42.0, "duration_hours": 1.0, "transformer_load": 90.0}
        long_inputs = {"temperature": 42.0, "duration_hours": 12.0, "transformer_load": 90.0}

        res_short = self.engine.simulate_digital_twin("SITE-001", short_inputs)
        res_long = self.engine.simulate_digital_twin("SITE-001", long_inputs)

        self.assertGreater(res_long["scenario"]["system_risk"], res_short["scenario"]["system_risk"])

    def test_equipment_failure_toggles(self):
        norm_inputs = {"temperature": 35.0, "transformer_load": 80.0}
        fail_inputs = {"temperature": 35.0, "transformer_load": 80.0, "toggle_cooling_failure": True}

        res_norm = self.engine.simulate_digital_twin("SITE-002", norm_inputs)
        res_fail = self.engine.simulate_digital_twin("SITE-002", fail_inputs)

        self.assertGreater(res_fail["equipment"]["transformer"]["risk"], res_norm["equipment"]["transformer"]["risk"])

    def test_intervention_strategy_simulation(self):
        inputs = {"temperature": 44.0, "humidity": 90.0, "transformer_load": 95.0, "chiller_capacity": 60.0}
        interventions = self.engine.simulate_interventions("SITE-003", inputs, baseline_risk=25.0)

        self.assertGreaterEqual(len(interventions), 5)
        # Combined strategy should produce lowest risk / highest resilience
        best = min(interventions, key=lambda x: x["simulated_system_risk"])
        self.assertEqual(best["strategy"], "Combined Optimization Strategy")

    def test_honest_ml_integration_status(self):
        inputs = {"temperature": 35.0}
        res = self.engine.simulate_digital_twin("SITE-001", inputs)
        ml_info = res.get("ml_integration", {})
        self.assertIn("ml_available", ml_info)
        self.assertIn("ml_status_text", ml_info)


if __name__ == "__main__":
    unittest.main()

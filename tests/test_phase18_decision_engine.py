"""
tests/test_phase18_decision_engine.py
=======================================
Phase 18 Automated Test Suite: AI-Powered Climate Resilience Decision & Response Engine

Tests Impact Engine, Urgency Engine, Recommendation Engine Phase 18, Action Priority Scoring,
Cascading Risk Detection, Multi-Timeline Response Plans, Action Status Tracking, and API outputs.
"""

import sys
import unittest
from pathlib import Path

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from site_registry import SiteRegistry
from api_clients.weather_client import WeatherAPIClient
from services.impact_engine import impact_engine, EQUIPMENT_CRITICALITY
from services.urgency_engine import urgency_engine
from services.recommendation_engine_phase18 import recommendation_engine_p18
from services.decision_engine import decision_engine, get_action_priority_level, ACTION_PRIORITY_CONFIG


class TestPhase18DecisionEngine(unittest.TestCase):

    def test_impact_engine_calculations(self):
        # Transformer criticality = 90
        res_tx = impact_engine.calculate_equipment_impact("transformer", risk_score=85.0, climate_stress=60.0)
        self.assertEqual(res_tx["equipment_type"], "transformer")
        self.assertEqual(res_tx["criticality_score"], 90.0)
        self.assertTrue(0.0 <= res_tx["impact_score"] <= 100.0)
        self.assertIn(res_tx["impact_level"], ["LOW", "MODERATE", "HIGH", "CRITICAL"])
        self.assertTrue(res_tx["cascading_potential"])

        # Water Pump criticality = 60; risk = 10, climate = 10 -> score = 0.5*10 + 0.3*60 + 0.2*10 = 25.0 (LOW)
        res_wp = impact_engine.calculate_equipment_impact("water_pump", risk_score=10.0, climate_stress=10.0)
        self.assertEqual(res_wp["criticality_score"], 60.0)
        self.assertEqual(res_wp["impact_level"], "LOW")

    def test_urgency_engine_calculations(self):
        # Critical urgency with sudden spike
        res_urg_crit = urgency_engine.calculate_urgency(
            risk_score=85.0, forecast_trend="SUDDEN SPIKE", trend_delta_24h=18.0, peak_risk_24h=95.0
        )
        self.assertEqual(res_urg_crit["urgency_level"], "CRITICAL")
        self.assertEqual(res_urg_crit["recommended_timeframe"], "Within 2 Hours")
        self.assertTrue(res_urg_crit["urgency_score"] >= 80.0)

        # Low urgency
        res_urg_low = urgency_engine.calculate_urgency(
            risk_score=15.0, forecast_trend="STABLE", trend_delta_24h=0.0, peak_risk_24h=18.0
        )
        self.assertEqual(res_urg_low["urgency_level"], "LOW")
        self.assertEqual(res_urg_low["recommended_timeframe"], "Routine / Next 48 Hours")

    def test_recommendation_engine_climate_drivers(self):
        # Heat Driver
        w_heat = {"temperature": 39.5, "peak_forecast_temp": 42.0, "humidity": 65.0, "realtime": True}
        driver_res = recommendation_engine_p18.identify_climate_driver(w_heat)
        self.assertEqual(driver_res["primary_driver"], "HEAT")

        # Action Decision for Transformer under Heat
        imp_info = {"impact_score": 80.0, "impact_level": "CRITICAL"}
        urg_info = {"recommended_timeframe": "Within 2 Hours", "urgency_level": "CRITICAL"}
        rec_res = recommendation_engine_p18.generate_action_decision(
            "Coimbatore Industrial Facility", "TX-001", "transformer", 85.0, w_heat, imp_info, urg_info
        )
        self.assertEqual(rec_res["equipment_id"], "TX-001")
        self.assertEqual(rec_res["priority"], "CRITICAL")
        self.assertIn("cooling", rec_res["action"].lower())
        self.assertIn("Electrical Operations", rec_res["responsible_team"])
        self.assertTrue(rec_res["decision_confidence_pct"] >= 80.0)
        self.assertEqual(rec_res["confidence_level"], "HIGH")

    def test_decision_engine_action_priority_scoring(self):
        # Formula check: 0.35*Risk + 0.25*Impact + 0.20*Urgency + 0.15*Criticality + 0.05*Climate
        prio_res = decision_engine.calculate_action_priority_score(
            risk_score=80.0,
            impact_score=75.0,
            urgency_score=90.0,
            criticality_score=90.0,
            climate_stress=70.0
        )
        # Expected = 0.35*80 + 0.25*75 + 0.20*90 + 0.15*90 + 0.05*70 = 28 + 18.75 + 18 + 13.5 + 3.5 = 81.75
        self.assertEqual(prio_res["action_priority_score"], 81.75)
        self.assertEqual(prio_res["action_priority_level"], "CRITICAL")

        # Configurable Level Threshold test
        self.assertEqual(get_action_priority_level(15.0), "LOW")
        self.assertEqual(get_action_priority_level(30.0), "MODERATE")
        self.assertEqual(get_action_priority_level(50.0), "HIGH")
        self.assertEqual(get_action_priority_level(75.0), "URGENT")
        self.assertEqual(get_action_priority_level(95.0), "CRITICAL")

    def test_cascading_risk_detection(self):
        w_extreme = {"temperature": 40.5, "peak_forecast_temp": 43.0, "humidity": 70.0}
        eq_risks = {
            "transformer": {"risk_score": 75.0},
            "chiller": {"risk_score": 70.0},
            "water_pump": {"risk_score": 30.0}
        }
        casc_res = decision_engine.detect_cascading_risk(eq_risks, w_extreme)
        self.assertTrue(casc_res["cascading_risk_detected"])
        self.assertIn("HEAT CASCADE DETECTED", casc_res["chain_description"])

    def test_evaluate_facility_decisions_end_to_end(self):
        registry = SiteRegistry()
        weather_client = WeatherAPIClient()
        site_1 = registry.get_site("SITE-001")
        w_norm = weather_client.get_current_data(
            location=site_1.get("city"),
            latitude=site_1.get("latitude"),
            longitude=site_1.get("longitude"),
            site_id="SITE-001"
        )
        dec_res = decision_engine.evaluate_facility_decisions(site_1, w_norm["data"])

        self.assertEqual(dec_res["site_id"], "SITE-001")
        self.assertIn("overall_risk", dec_res)
        self.assertIn("facility_priority_score", dec_res)
        self.assertIsNotNone(dec_res["top_action"])
        self.assertEqual(len(dec_res["decisions"]), 3)
        self.assertIn("response_plan", dec_res)
        self.assertIn("now", dec_res["response_plan"]["timelines"])

    def test_action_status_tracker(self):
        registry = SiteRegistry()
        weather_client = WeatherAPIClient()
        site_1 = registry.get_site("SITE-001")
        w_norm = weather_client.get_current_data(
            location=site_1.get("city"),
            latitude=site_1.get("latitude"),
            longitude=site_1.get("longitude"),
            site_id="SITE-001"
        )
        dec_res = decision_engine.evaluate_facility_decisions(site_1, w_norm["data"])

        action_id = dec_res["decisions"][0]["action_id"]

        # Update status to ACKNOWLEDGED
        ok1 = decision_engine.update_action_status(action_id, "ACKNOWLEDGED")
        self.assertTrue(ok1)
        tracker = decision_engine.get_action_tracker()
        self.assertEqual(tracker[action_id]["status"], "ACKNOWLEDGED")
        self.assertIsNotNone(tracker[action_id].get("acknowledged_at"))

        # Update status to IN_PROGRESS
        ok2 = decision_engine.update_action_status(action_id, "IN_PROGRESS")
        self.assertTrue(ok2)
        self.assertEqual(tracker[action_id]["status"], "IN_PROGRESS")


if __name__ == "__main__":
    unittest.main()

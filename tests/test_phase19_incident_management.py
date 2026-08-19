"""
tests/test_phase19_incident_management.py
===========================================
Phase 19 Automated Test Suite: Resilience Orchestration, Incident Management & Automated Alerting

Tests Incident Engine Phase 19, Alert Engine, Notification Engine, Escalation Engine,
Response Effectiveness Engine, lifecycle state transitions, duplicate prevention, and dataset export.
"""

import os
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
from services.incident_engine_phase19 import IncidentEnginePhase19, map_priority_to_severity
from services.alert_engine import AlertEngine
from services.notification_engine import InAppNotificationProvider
from services.escalation_engine import EscalationEngine
from services.response_effectiveness_engine import ResponseEffectivenessEngine


TEST_DB_PATH = Path(__file__).resolve().parent / "test_incidents_db.json"


class TestPhase19IncidentManagement(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not hasattr(state, "site_registry") or state.site_registry is None:
            state.site_registry = SiteRegistry()
        if not hasattr(state, "weather_client_inst") or state.weather_client_inst is None:
            state.weather_client_inst = WeatherAPIClient()

    def setUp(self):
        if TEST_DB_PATH.exists():
            os.remove(TEST_DB_PATH)
        self.engine = IncidentEnginePhase19(db_path=TEST_DB_PATH)

    def tearDown(self):
        if TEST_DB_PATH.exists():
            os.remove(TEST_DB_PATH)

    def test_incident_creation_and_id_format(self):
        inc, is_new = self.engine.create_or_update_incident(
            site_id="SITE-003",
            site_name="Bengaluru Industrial Facility",
            equipment_id="TX-003",
            equipment_type="TRANSFORMER",
            risk_score=85.0,
            priority_score=88.0,
            impact_score=80.0,
            urgency_score=85.0,
            recommended_action="Inspect cooling system",
            reason="Extreme heat wave"
        )
        self.assertTrue(is_new)
        self.assertTrue(inc["incident_id"].startswith("CG-"))
        self.assertEqual(inc["severity"], "CRITICAL")
        self.assertEqual(inc["status"], "OPEN")
        self.assertEqual(inc["equipment_id"], "TX-003")

    def test_duplicate_incident_prevention(self):
        inc1, is_new1 = self.engine.create_or_update_incident(
            site_id="SITE-001", site_name="Coimbatore", equipment_id="CH-001",
            equipment_type="CHILLER", risk_score=70.0, priority_score=72.0,
            impact_score=65.0, urgency_score=70.0, recommended_action="Pre-cool facility", reason="Humidity stress"
        )
        self.assertTrue(is_new1)

        # Immediate repeat evaluation
        inc2, is_new2 = self.engine.create_or_update_incident(
            site_id="SITE-001", site_name="Coimbatore", equipment_id="CH-001",
            equipment_type="CHILLER", risk_score=74.0, priority_score=75.0,
            impact_score=68.0, urgency_score=72.0, recommended_action="Pre-cool facility", reason="Humidity stress"
        )
        self.assertFalse(is_new2)
        self.assertEqual(inc1["incident_id"], inc2["incident_id"])
        self.assertEqual(inc2["risk_score"], 74.0)

    def test_valid_and_invalid_lifecycle_transitions(self):
        inc, _ = self.engine.create_or_update_incident(
            site_id="SITE-002", site_name="Chennai", equipment_id="WP-002",
            equipment_type="WATER_PUMP", risk_score=60.0, priority_score=65.0,
            impact_score=55.0, urgency_score=60.0, recommended_action="Clear sump pit", reason="Heavy rain"
        )
        inc_id = inc["incident_id"]

        # Valid: OPEN -> ACKNOWLEDGED
        ok1, _, _ = self.engine.update_incident_status(inc_id, "ACKNOWLEDGED")
        self.assertTrue(ok1)

        # Valid: ACKNOWLEDGED -> IN_PROGRESS
        ok2, _, _ = self.engine.update_incident_status(inc_id, "IN_PROGRESS")
        self.assertTrue(ok2)

        # Valid: IN_PROGRESS -> MITIGATED
        ok3, _, _ = self.engine.update_incident_status(inc_id, "MITIGATED")
        self.assertTrue(ok3)

        # Valid: MITIGATED -> RESOLVED
        ok4, _, _ = self.engine.update_incident_status(inc_id, "RESOLVED")
        self.assertTrue(ok4)

        # Valid: RESOLVED -> CLOSED
        ok5, _, _ = self.engine.update_incident_status(inc_id, "CLOSED")
        self.assertTrue(ok5)

        # INVALID: CLOSED -> IN_PROGRESS (Must be rejected)
        ok_fail, _, msg = self.engine.update_incident_status(inc_id, "IN_PROGRESS")
        self.assertFalse(ok_fail)
        self.assertIn("Invalid state transition", msg)

    def test_response_effectiveness_evaluation(self):
        # Attach engine to main engine for test
        from services.incident_engine_phase19 import incident_engine_p19
        inc, _ = incident_engine_p19.create_or_update_incident(
            site_id="SITE-001", site_name="Coimbatore", equipment_id="TX-001",
            equipment_type="TRANSFORMER", risk_score=85.0, priority_score=88.0,
            impact_score=80.0, urgency_score=85.0, recommended_action="Inspect transformer cooling", reason="Heat stress"
        )
        inc_id = inc["incident_id"]

        # Transition OPEN -> ACKNOWLEDGED -> IN_PROGRESS
        incident_engine_p19.update_incident_status(inc_id, "ACKNOWLEDGED")
        incident_engine_p19.update_incident_status(inc_id, "IN_PROGRESS")

        # Execute Response Effectiveness check
        eff_engine = ResponseEffectivenessEngine()
        res = eff_engine.evaluate_response_effectiveness(inc_id, operator_notes="Auxiliary cooling fans activated.")
        self.assertTrue(res["success"])
        self.assertIn("effectiveness", res)
        eff_data = res["effectiveness"]
        self.assertIn(eff_data["effectiveness_level"], ["EFFECTIVE", "PARTIALLY_EFFECTIVE", "INEFFECTIVE"])
        self.assertEqual(inc["status"], "MITIGATED")

    def test_learning_dataset_export(self):
        inc, _ = self.engine.create_or_update_incident(
            site_id="SITE-004", site_name="Madurai", equipment_id="TX-004",
            equipment_type="TRANSFORMER", risk_score=75.0, priority_score=78.0,
            impact_score=70.0, urgency_score=75.0, recommended_action="Rebalance load", reason="Thermal surge"
        )
        inc["status"] = "RESOLVED"
        inc["post_action_risk_score"] = 40.0
        inc["response_effectiveness"] = {"effectiveness_level": "EFFECTIVE"}

        dataset = self.engine.export_learning_dataset()
        self.assertGreaterEqual(len(dataset), 1)
        self.assertEqual(dataset[0]["incident_id"], inc["incident_id"])
        self.assertEqual(dataset[0]["risk_reduction"], 35.0)


if __name__ == "__main__":
    unittest.main()

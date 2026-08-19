"""
tests/test_phase22_optimization.py
===================================
Phase 22 Automated Test Suite: Resilience Optimization & Prescriptive Action Planner

Tests intervention library retrieval, multi-attribute objective plan scoring, plan ranking,
selection of recommended/second-best/lowest-disruption/max-risk-reduction options,
sensitivity analysis, temperature robustness testing, human approval workflow, and promotion to Phase 19 Incident Management.
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
from services.intervention_library import intervention_library
from services.optimization_engine import optimization_engine


class TestPhase22ResilienceOptimization(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not hasattr(state, "site_registry") or state.site_registry is None:
            state.site_registry = SiteRegistry()
        if not hasattr(state, "weather_client_inst") or state.weather_client_inst is None:
            state.weather_client_inst = WeatherAPIClient()

    def test_intervention_library(self):
        strats = intervention_library.get_all_strategies()
        self.assertEqual(len(strats), 10)

        pre_cool = intervention_library.get_strategy("PRE_COOLING")
        self.assertIsNotNone(pre_cool)
        self.assertEqual(pre_cool["resource_level"], "LOW")
        self.assertEqual(pre_cool["operational_disruption"], "LOW")

    def test_objective_score_calculation_and_classification(self):
        score_opt = optimization_engine.compute_plan_objective_score(34.0, "MEDIUM", 45, "HIGH", "HIGH")
        self.assertGreaterEqual(score_opt, 0.0)
        self.assertLessEqual(score_opt, 100.0)

        self.assertEqual(optimization_engine.classify_plan_score(85.0), "OPTIMAL")
        self.assertEqual(optimization_engine.classify_plan_score(70.0), "STRONG")
        self.assertEqual(optimization_engine.classify_plan_score(50.0), "ACCEPTABLE")
        self.assertEqual(optimization_engine.classify_plan_score(30.0), "LIMITED")
        self.assertEqual(optimization_engine.classify_plan_score(10.0), "POOR")

    def test_prescriptive_optimization_execution(self):
        scenario_inputs = {
            "temperature": 43.0,
            "humidity": 88.0,
            "rainfall": 15.0,
            "duration_hours": 8.0,
            "transformer_load": 95.0,
            "transformer_cooling": 70.0,
            "chiller_capacity": 60.0,
            "pump_flow": 85.0
        }
        opt = optimization_engine.optimize_response("SITE-003", scenario_inputs)

        self.assertIsNotNone(opt)
        self.assertIn("optimization_id", opt)
        self.assertEqual(opt["site_id"], "SITE-003")
        self.assertEqual(opt["lifecycle_status"], "RECOMMENDED")
        self.assertIn("recommended_plan", opt)
        self.assertIn("second_best_option", opt)
        self.assertIn("lowest_disruption_option", opt)
        self.assertIn("max_risk_reduction_option", opt)
        self.assertGreater(len(opt["candidate_plans"]), 5)
        self.assertEqual(len(opt["action_timeline"]), 5)

    def test_sensitivity_and_robustness_analysis(self):
        scenario_inputs = {"temperature": 42.0, "transformer_load": 90.0}
        sens = optimization_engine.calculate_sensitivity("SITE-001", scenario_inputs)
        self.assertGreaterEqual(len(sens), 4)
        self.assertIn("variable", sens[0])

        rob = optimization_engine.calculate_robustness("SITE-001", scenario_inputs, "COMBINED_RESILIENCE_PLAN")
        self.assertIn("is_robust", rob)
        self.assertIn("status_badge", rob)

    def test_human_approval_rejection_and_promotion_workflow(self):
        scenario_inputs = {"temperature": 44.0, "transformer_load": 95.0}
        opt = optimization_engine.optimize_response("SITE-002", scenario_inputs)
        opt_id = opt["optimization_id"]

        # Approve Plan
        app_res = optimization_engine.approve_plan(opt_id, "Chief Resilience Engineer")
        self.assertEqual(app_res["lifecycle_status"], "APPROVED")
        self.assertEqual(app_res["approved_by"], "Chief Resilience Engineer")

        # Promote to Phase 19 Incident Management
        prom_res = optimization_engine.promote_plan_to_incident(opt_id)
        self.assertTrue(prom_res["success"])
        self.assertIn("promoted_incident_id", prom_res["optimization"])
        self.assertEqual(prom_res["optimization"]["lifecycle_status"], "IN_PROGRESS")

        # Reject Plan Test
        opt2 = optimization_engine.optimize_response("SITE-001", scenario_inputs)
        rej_res = optimization_engine.reject_plan(opt2["optimization_id"], "Load reduction unacceptable for process continuity")
        self.assertEqual(rej_res["lifecycle_status"], "REJECTED")


if __name__ == "__main__":
    unittest.main()

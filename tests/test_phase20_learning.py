"""
tests/test_phase20_learning.py
===============================
Phase 20 Automated Test Suite: Continuous Learning, Adaptive AI & Predictive Maintenance Intelligence

Tests Data Quality Validation, Feature Engineering, Facility/Equipment Baselines, Statistical Anomaly Detection,
ML Eligibility Checks, Model Training, Model Registry, Model Activation, Model Rollback, and Adaptive Intelligence.
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
from services.historical_analytics_engine import HistoricalAnalyticsEngine
from services.feature_engineering_engine import FeatureEngineeringEngine
from services.anomaly_detection_engine import AnomalyDetectionEngine
from services.model_registry import ModelRegistry
from services.ml_training_engine import MLTrainingEngine
from services.recommendation_learning_engine import RecommendationLearningEngine
from services.adaptive_risk_engine import AdaptiveRiskEngine


TEST_REGISTRY_PATH = Path(__file__).resolve().parent / "test_model_registry.json"


class TestPhase20ContinuousLearning(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not hasattr(state, "site_registry") or state.site_registry is None:
            state.site_registry = SiteRegistry()
        if not hasattr(state, "weather_client_inst") or state.weather_client_inst is None:
            state.weather_client_inst = WeatherAPIClient()

    def setUp(self):
        if TEST_REGISTRY_PATH.exists():
            os.remove(TEST_REGISTRY_PATH)
        self.registry = ModelRegistry(registry_path=TEST_REGISTRY_PATH)
        self.trainer = MLTrainingEngine(min_records=100)
        self.analytics = HistoricalAnalyticsEngine()
        self.feature_eng = FeatureEngineeringEngine()
        self.anomaly_eng = AnomalyDetectionEngine()

    def tearDown(self):
        if TEST_REGISTRY_PATH.exists():
            os.remove(TEST_REGISTRY_PATH)

    def test_data_quality_validation(self):
        mock_incidents = [
            {"site_id": "SITE-001", "equipment_id": "TX-001", "created_at": "2026-08-18 10:00:00", "risk_score": 85.0},
            {"site_id": "SITE-001", "equipment_id": "TX-001", "created_at": "2026-08-18 10:00:00", "risk_score": 85.0},  # Duplicate
            {"site_id": None, "equipment_id": "CH-001", "created_at": "2026-08-18 11:00:00", "risk_score": 70.0},        # Missing site
            {"site_id": "SITE-002", "equipment_id": "WP-002", "created_at": "2026-08-18 12:00:00", "risk_score": 150.0}   # Out of bounds
        ]
        dq = self.analytics.validate_data_quality(mock_incidents)
        self.assertEqual(dq["total_records"], 4)
        self.assertEqual(dq["valid_records"], 1)
        self.assertEqual(dq["duplicate_records_count"], 1)
        self.assertEqual(dq["missing_values_count"], 1)
        self.assertEqual(dq["invalid_records"], 1)
        self.assertEqual(dq["data_quality_pct"], 25.0)

    def test_feature_engineering_and_data_leakage_prevention(self):
        mock_inc = {
            "site_id": "SITE-001",
            "equipment_id": "TX-001",
            "equipment_type": "TRANSFORMER",
            "risk_score": 85.0,
            "pre_action_risk_score": 85.0,
            "post_action_risk_score": 10.0,
            "impact_score": 80.0,
            "urgency_score": 85.0,
            "severity": "CRITICAL",
            "created_at": "2026-08-18 14:00:00"
        }
        f_dict = self.feature_eng.extract_features(mock_inc)
        self.assertEqual(f_dict["pre_action_risk"], 85.0)
        self.assertNotIn("post_action_risk_score", f_dict)  # Excluded to prevent data leakage
        self.assertEqual(f_dict["high_risk_target"], 1)

    def test_statistical_anomaly_detection(self):
        site = state.site_registry.get_site("SITE-001")
        anomalies = self.anomaly_eng.evaluate_site_anomalies(site)
        self.assertGreater(len(anomalies), 0)
        for a in anomalies:
            self.assertIn("anomaly_score", a)
            self.assertIn("classification", a)
            self.assertIn("explanation", a)
            self.assertIn(a["classification"], ["NORMAL", "MINOR", "MODERATE", "SIGNIFICANT", "SEVERE"])

    def test_ml_eligibility_insufficient_data(self):
        small_incidents = [
            {"site_id": "SITE-001", "equipment_id": "TX-001", "created_at": "2026-08-18 10:00:00", "risk_score": 85.0, "severity": "CRITICAL"}
        ]
        elig = self.trainer.check_eligibility(small_incidents)
        self.assertFalse(elig["ml_ready"])
        self.assertIn("Insufficient historical labeled incidents", elig["reason"])

        res = self.trainer.train_and_evaluate_model(force_train=False, incidents=small_incidents)
        self.assertFalse(res["success"])
        self.assertIn("Insufficient", res["error"])

    def test_model_training_evaluation_and_registry(self):
        # Create synthetic dataset with 20 records for force_train test
        synth_incidents = []
        for i in range(25):
            r = 85.0 if i % 2 == 0 else 30.0
            synth_incidents.append({
                "site_id": f"SITE-00{(i%5)+1}",
                "equipment_id": f"TX-00{i}",
                "equipment_type": "TRANSFORMER" if i % 2 == 0 else "CHILLER",
                "risk_score": r,
                "impact_score": r,
                "urgency_score": r,
                "severity": "CRITICAL" if r > 60 else "MODERATE",
                "created_at": f"2026-08-18 10:{i:02d}:00"
            })

        res = self.trainer.train_and_evaluate_model(model_type="RandomForest", force_train=True, incidents=synth_incidents)
        self.assertTrue(res["success"])
        self.assertIn("metrics", res)
        metrics = res["metrics"]
        self.assertIn("accuracy", metrics)
        self.assertIn("f1", metrics)

        # Verify model registration
        from services.model_registry import model_registry
        all_models = model_registry.get_all_models()
        self.assertGreaterEqual(len(all_models), 1)


    def test_model_activation_and_rollback(self):
        m1 = self.registry.register_model("RiskModel-v1.0", "v1.0", "RandomForest", "ds1", ["f1"], {"f1": 0.85})
        m2 = self.registry.register_model("RiskModel-v2.0", "v2.0", "RandomForest", "ds2", ["f1"], {"f1": 0.90})

        # Activate v1.0
        ok1 = self.registry.activate_model("RiskModel-v1.0")
        self.assertTrue(ok1)
        self.assertEqual(self.registry.get_active_model()["model_id"], "RiskModel-v1.0")

        # Activate v2.0 -> v1.0 becomes RETIRED
        ok2 = self.registry.activate_model("RiskModel-v2.0")
        self.assertTrue(ok2)
        self.assertEqual(self.registry.get_active_model()["model_id"], "RiskModel-v2.0")

        # Rollback -> v2.0 becomes RETIRED, v1.0 becomes ACTIVE
        rolled_back = self.registry.rollback_model()
        self.assertIsNotNone(rolled_back)
        self.assertEqual(rolled_back["model_id"], "RiskModel-v1.0")
        self.assertEqual(self.registry.get_active_model()["model_id"], "RiskModel-v1.0")

    def test_adaptive_risk_and_recommendations(self):
        adaptive_eng = AdaptiveRiskEngine()
        advisories = adaptive_eng.get_advisory_thresholds()
        self.assertGreater(len(advisories), 0)
        for adv in advisories:
            self.assertTrue(adv["is_advisory_only"])
            self.assertIn("advisory_warning_threshold", adv)

        rec_eng = RecommendationLearningEngine()
        learned = rec_eng.get_learned_recommendations("HEAT", "TRANSFORMER")
        self.assertIsInstance(learned, list)


if __name__ == "__main__":
    unittest.main()

"""
backend/services/learning_engine.py
===================================
Phase 20 — Continuous Learning, Adaptive AI & Predictive Maintenance Intelligence

Master Learning Engine coordinating data quality, facility/equipment baselines,
statistical anomaly detection, ML eligibility, model registry, and learning insights.
"""

import time
from typing import Dict, Any, List

from services.historical_analytics_engine import historical_analytics_engine
from services.anomaly_detection_engine import anomaly_detection_engine
from services.ml_training_engine import ml_training_engine
from services.model_registry import model_registry
from services.recommendation_learning_engine import recommendation_learning_engine
from services.adaptive_risk_engine import adaptive_risk_engine


class LearningEngine:
    """Master Learning Engine integrating analytics, anomaly detection, and ML capabilities."""

    @staticmethod
    def generate_explainable_insights() -> List[str]:
        """Generates human-readable, data-backed operational learning insights."""
        insights = []

        # 1. Baseline insights
        facs = historical_analytics_engine.get_facility_baselines()
        if facs:
            top_fac = max(facs.values(), key=lambda x: x["average_risk_score"])
            insights.append(
                f"Historical observations indicate {top_fac['site_name']} ({top_fac['site_id']}) "
                f"experiences the highest average baseline risk score ({top_fac['average_risk_score']}/100) under {top_fac['typical_climate_driver']} stress."
            )

        # 2. Intervention effectiveness insights
        interventions = historical_analytics_engine.get_intervention_effectiveness_analysis()
        if interventions:
            top_act = interventions[0]
            insights.append(
                f"Historical response analysis shows '{top_act['action']}' produced the greatest "
                f"observed risk reduction (-{top_act['avg_risk_reduction_pts']} pts) across {top_act['sample_size']} evaluated incidents."
            )

        # 3. Anomaly insights
        anomalies = anomaly_detection_engine.detect_all_anomalies()
        severe_anoms = [a for a in anomalies if a["classification"] in ["SEVERE", "SIGNIFICANT"]]
        if severe_anoms:
            top_anom = severe_anoms[0]
            insights.append(
                f"Active Anomaly Detected: {top_anom['equipment_id']} at {top_anom['site_name']} "
                f"is operating {top_anom['deviation_pts']} pts above its historical facility baseline."
            )
        else:
            insights.append("Statistical anomaly detection indicates all regional equipment operating within expected baseline variance.")

        # 4. ML Eligibility insights
        elig = ml_training_engine.check_eligibility()
        if elig["ml_ready"]:
            insights.append(f"Supervised ML training dataset fully eligible ({elig['total_records']} verified records).")
        else:
            insights.append(f"Supervised ML dataset pending additional labeled events ({elig['total_records']} / {elig['required_records']} required). Analytics and anomaly detection active.")

        return insights

    def get_learning_summary(self) -> Dict[str, Any]:
        """Master summary object for AI Learning dashboard and APIs."""
        dq = historical_analytics_engine.validate_data_quality()
        elig = ml_training_engine.check_eligibility()
        active_model = model_registry.get_active_model()
        anomalies = anomaly_detection_engine.detect_all_anomalies()
        facs = historical_analytics_engine.get_facility_baselines()
        eqs = historical_analytics_engine.get_equipment_baselines()
        interventions = historical_analytics_engine.get_intervention_effectiveness_analysis()
        advisories = adaptive_risk_engine.get_advisory_thresholds()
        insights = self.generate_explainable_insights()

        return {
            "success": True,
            "data_health": dq,
            "ml_eligibility": elig,
            "active_model": active_model,
            "active_anomalies_count": len(anomalies),
            "anomalies": anomalies[:5],  # Top 5 anomalies
            "facility_baselines": facs,
            "equipment_baselines": eqs,
            "intervention_rankings": interventions,
            "advisory_thresholds": advisories,
            "learning_insights": insights,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }


learning_engine = LearningEngine()

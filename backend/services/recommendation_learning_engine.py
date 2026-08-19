"""
backend/services/recommendation_learning_engine.py
===================================================
Phase 20 — Continuous Learning, Adaptive AI & Predictive Maintenance Intelligence

Recommendation Learning Engine analyzing historical operator intervention outcomes
and ranking recommended actions with sample-size weighted evidence strength.
"""

import numpy as np
from typing import Dict, Any, List

from services.historical_analytics_engine import historical_analytics_engine
from services.incident_engine_phase19 import incident_engine_p19


class RecommendationLearningEngine:
    """Ranks preventive actions using empirical historical response outcomes."""

    def get_learned_recommendations(
        self, climate_driver: str = "HEAT", equipment_type: str = "TRANSFORMER"
    ) -> List[Dict[str, Any]]:
        """
        Ranks recommended operator actions for a specific climate driver and equipment type
        based on historical average risk reduction and evidence strength.
        """
        incidents = incident_engine_p19.get_all_incidents(active_only=False)

        # Filter relevant past incidents
        filtered = [
            inc for inc in incidents
            if str(inc.get("equipment_type", "")).upper() == equipment_type.upper()
            and inc.get("response_effectiveness") is not None
        ]

        if not filtered:
            filtered = [inc for inc in incidents if inc.get("response_effectiveness") is not None]

        action_outcomes: Dict[str, List[float]] = {}
        for inc in filtered:
            eff = inc["response_effectiveness"]
            act = inc.get("recommended_action", "Routine Inspection")
            red = float(eff.get("observed_risk_reduction_pts", 0.0))
            action_outcomes.setdefault(act, []).append(red)

        learned_list = []
        for act, red_list in action_outcomes.items():
            cnt = len(red_list)
            avg_red = round(float(np.mean(red_list)), 1) if red_list else 0.0

            if cnt >= 10:
                strength = "HIGH"
            elif cnt >= 3:
                strength = "MODERATE"
            else:
                strength = "LOW"

            explanation = (
                f"Historical evidence ({cnt} events, {strength} strength): '{act}' "
                f"produced an average observed risk reduction of {avg_red} points."
            )

            learned_list.append({
                "action": act,
                "sample_size": cnt,
                "avg_risk_reduction_pts": avg_red,
                "evidence_strength": strength,
                "explanation": explanation
            })

        learned_list.sort(key=lambda x: x["avg_risk_reduction_pts"], reverse=True)
        return learned_list


recommendation_learning_engine = RecommendationLearningEngine()

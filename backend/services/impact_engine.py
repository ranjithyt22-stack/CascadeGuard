"""
backend/services/impact_engine.py
==================================
Phase 18 — AI-Powered Climate Resilience Decision & Response Engine

Impact Engine evaluating equipment operational criticality and potential service
disruption severity. Computes explainable Operational Impact scores without false
financial calculations.
"""

import numpy as np
from typing import Dict, Any


# Base Equipment Criticality Scores (0-100)
EQUIPMENT_CRITICALITY = {
    "transformer": 90.0,   # Primary power distribution - highest facility impact
    "chiller": 75.0,       # Facility cooling & thermal control - high operational impact
    "water_pump": 60.0,    # Auxiliary cooling & drainage support - moderate impact
    "facility": 80.0       # Site-wide infrastructure composite
}


class ImpactEngine:
    """Evaluates operational impact and disruption severity for facility assets."""

    def calculate_equipment_impact(
        self, equipment_type: str, risk_score: float, climate_stress: float = 30.0
    ) -> Dict[str, Any]:
        """
        Calculates Operational Impact score (0-100) and impact category.
        Formula: 0.50 * risk_score + 0.30 * equipment_criticality + 0.20 * climate_stress
        """
        eq_type = str(equipment_type).lower().replace(" ", "_")
        criticality = EQUIPMENT_CRITICALITY.get(eq_type, 70.0)

        risk = float(np.clip(risk_score, 0.0, 100.0))
        c_stress = float(np.clip(climate_stress, 0.0, 100.0))

        impact_score = 0.50 * risk + 0.30 * criticality + 0.20 * c_stress
        impact_score = float(np.clip(impact_score, 0.0, 100.0))
        round_impact = round(impact_score, 2)

        if round_impact <= 25.0:
            impact_level = "LOW"
            disruption_desc = "Minimal operational disturbance. Baseline equipment load maintained."
        elif round_impact <= 50.0:
            impact_level = "MODERATE"
            disruption_desc = "Moderate operational drag. Requires monitoring during peak demand."
        elif round_impact <= 75.0:
            impact_level = "HIGH"
            disruption_desc = "High service disruption potential. Facility cooling/power margin reduced."
        else:
            impact_level = "CRITICAL"
            disruption_desc = "Severe facility disruption risk. High probability of forced outage if unmitigated."

        # Cascading impact potential flag
        cascading_potential = (risk > 65.0) and (criticality >= 75.0)

        return {
            "equipment_type": equipment_type,
            "impact_score": round_impact,
            "impact_level": impact_level,
            "criticality_score": criticality,
            "disruption_description": disruption_desc,
            "cascading_potential": cascading_potential
        }

    def calculate_facility_impact(
        self, facility_risk: float, equipment_impacts: Dict[str, Any], climate_stress: float = 30.0
    ) -> Dict[str, Any]:
        """Calculates overall facility-wide operational impact."""
        max_eq_impact = max(
            [imp.get("impact_score", 0.0) for imp in equipment_impacts.values()]
        ) if equipment_impacts else facility_risk

        facility_impact_score = round(float(np.clip(0.60 * max_eq_impact + 0.40 * facility_risk, 0.0, 100.0)), 2)

        if facility_impact_score <= 25.0:
            level = "LOW"
        elif facility_impact_score <= 50.0:
            level = "MODERATE"
        elif facility_impact_score <= 75.0:
            level = "HIGH"
        else:
            level = "CRITICAL"

        return {
            "facility_impact_score": facility_impact_score,
            "facility_impact_level": level,
            "max_equipment_impact_score": max_eq_impact
        }


impact_engine = ImpactEngine()

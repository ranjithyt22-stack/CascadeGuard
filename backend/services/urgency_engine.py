"""
backend/services/urgency_engine.py
===================================
Phase 18 — AI-Powered Climate Resilience Decision & Response Engine

Urgency Engine evaluating time urgency, rate of risk escalation, and forecast peak timing
to assign actionable response timeframes.
"""

import numpy as np
from typing import Dict, Any


class UrgencyEngine:
    """Evaluates time urgency and response timeframes for operational decisions."""

    def calculate_urgency(
        self,
        risk_score: float,
        forecast_trend: str = "STABLE",
        trend_delta_24h: float = 0.0,
        peak_risk_24h: float = None
    ) -> Dict[str, Any]:
        """
        Calculates time urgency score (0-100), urgency level, and response timeframe.
        """
        risk = float(np.clip(risk_score, 0.0, 100.0))
        delta = float(trend_delta_24h) if trend_delta_24h is not None else 0.0
        peak = float(peak_risk_24h) if peak_risk_24h is not None else risk


        # Base urgency driven by risk score
        base_urgency = risk * 0.60

        # Rate of increase bonus
        trend_bonus = 0.0
        if forecast_trend == "SUDDEN SPIKE" or delta >= 15.0:
            trend_bonus = 35.0
        elif forecast_trend == "RISING" or delta > 3.0:
            trend_bonus = 20.0
        elif forecast_trend == "FALLING" or delta < -3.0:
            trend_bonus = -10.0

        # Peak risk bonus
        peak_bonus = max(0.0, (peak - risk) * 0.40)

        urgency_score = base_urgency + trend_bonus + peak_bonus
        urgency_score = float(np.clip(urgency_score, 0.0, 100.0))
        round_urgency = round(urgency_score, 2)

        if round_urgency >= 80.0 or risk >= 80.0:
            urgency_level = "CRITICAL"
            timeframe = "Within 2 Hours"
            reason = "High immediate risk score combined with escalating thermal forecast trend."
        elif round_urgency >= 60.0 or (risk >= 60.0 and delta > 0):
            urgency_level = "URGENT"
            timeframe = "Within 6 Hours"
            reason = "Elevated risk expected to increase during peak forecast weather window."
        elif round_urgency >= 40.0:
            urgency_level = "HIGH"
            timeframe = "Within 12 Hours"
            reason = "Moderate risk trajectory requiring intervention before peak daily load."
        elif round_urgency >= 20.0:
            urgency_level = "MODERATE"
            timeframe = "Within 24 Hours"
            reason = "Stable moderate risk. Action should be scheduled during routine maintenance shift."
        else:
            urgency_level = "LOW"
            timeframe = "Routine / Next 48 Hours"
            reason = "Low risk baseline. Standard operational monitoring."

        return {
            "urgency_score": round_urgency,
            "urgency_level": urgency_level,
            "recommended_timeframe": timeframe,
            "urgency_reason": reason,
            "rate_of_increase_pts": round(delta, 2)
        }


urgency_engine = UrgencyEngine()

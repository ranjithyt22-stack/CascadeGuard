"""
backend/services/adaptive_risk_engine.py
=========================================
Phase 20 — Continuous Learning, Adaptive AI & Predictive Maintenance Intelligence

Adaptive Risk Engine generating advisory, reviewable threshold adaptations based on facility
and equipment baseline deviations without silently overriding Phase 17 safety controls.
"""

import time
from typing import Dict, Any, List

from services.historical_analytics_engine import historical_analytics_engine


GLOBAL_WARNING_THRESHOLD = 70.0
GLOBAL_CRITICAL_THRESHOLD = 85.0


class AdaptiveRiskEngine:
    """Computes non-overriding advisory adaptive thresholds based on empirical historical baselines."""

    def get_advisory_thresholds(self) -> List[Dict[str, Any]]:
        """
        Calculates advisory adaptive thresholds for registered facilities
        based on historical risk averages and stress thresholds.
        """
        fac_baselines = historical_analytics_engine.get_facility_baselines()
        advisories = []

        for site_id, b in fac_baselines.items():
            site_name = b.get("site_name", site_id)
            avg_risk = b.get("average_risk_score", 50.0)

            # Calculate advisory warning threshold (85% of elevated average or baseline)
            advisory_warn = round(float(max(55.0, min(80.0, avg_risk * 1.1))), 1)
            advisory_crit = round(float(max(75.0, min(95.0, avg_risk * 1.25))), 1)

            diff_warn = round(advisory_warn - GLOBAL_WARNING_THRESHOLD, 1)

            if abs(diff_warn) >= 3.0:
                reason = (
                    f"Historical asset behavior at {site_name} indicates elevated stress beginning at risk {advisory_warn} "
                    f"(Global warning threshold: {GLOBAL_WARNING_THRESHOLD})."
                )
            else:
                reason = f"{site_name} baseline aligns closely with global safety thresholds."

            advisories.append({
                "site_id": site_id,
                "site_name": site_name,
                "global_warning_threshold": GLOBAL_WARNING_THRESHOLD,
                "global_critical_threshold": GLOBAL_CRITICAL_THRESHOLD,
                "advisory_warning_threshold": advisory_warn,
                "advisory_critical_threshold": advisory_crit,
                "baseline_average_risk": avg_risk,
                "deviation_from_global": diff_warn,
                "advisory_reason": reason,
                "is_advisory_only": True,
                "evaluated_at": time.strftime("%Y-%m-%d %H:%M:%S")
            })

        return advisories


adaptive_risk_engine = AdaptiveRiskEngine()

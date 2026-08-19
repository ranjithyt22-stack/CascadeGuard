"""
backend/services/escalation_engine.py
======================================
Phase 19 — Resilience Orchestration, Incident Management & Automated Alerting

Escalation Engine monitoring unacknowledged incidents and overdue actions,
escalating alert severity and logging audit events when response timeframes expire.
"""

import time
from typing import Dict, Any, List

from services.incident_engine_phase19 import incident_engine_p19
from services.alert_engine import alert_engine_p19


# Configurable Escalation Timeouts (in seconds)
ESCALATION_TIMEOUTS = {
    "CRITICAL": 900,   # 15 minutes
    "URGENT": 1800,    # 30 minutes
    "HIGH": 7200,      # 2 hours
    "MODERATE": 14400  # 4 hours
}


class EscalationEngine:
    """Monitors overdue incidents and escalates alert severity."""

    def __init__(self, timeouts: Dict[str, int] = None):
        self.timeouts = timeouts or ESCALATION_TIMEOUTS

    def evaluate_escalations(self) -> List[Dict[str, Any]]:
        """Scans active unacknowledged incidents and triggers escalations if overdue."""
        active_incidents = incident_engine_p19.get_all_incidents(active_only=True)
        escalated_list = []
        now_ts = time.time()

        for inc in active_incidents:
            status = inc.get("status")
            sev = inc.get("severity", "MODERATE")
            inc_id = inc.get("incident_id")
            c_str = inc.get("created_at")

            if not c_str or status != "OPEN":
                continue

            try:
                c_ts = time.mktime(time.strptime(c_str, "%Y-%m-%d %H:%M:%S"))
                elapsed = now_ts - c_ts
                limit = self.timeouts.get(sev, 7200)

                if elapsed >= limit and not inc.get("escalated_flag"):
                    inc["escalated_flag"] = True
                    # Escalate severity level if possible
                    new_sev = "CRITICAL" if sev in ["HIGH", "URGENT"] else "URGENT"
                    inc["severity"] = new_sev

                    # Log escalation
                    incident_engine_p19.log_event(
                        inc_id,
                        "ACTION_OVERDUE",
                        f"Incident response timeframe expired ({int(elapsed/60)} min). Escalated severity to {new_sev}.",
                        actor="EscalationEngine"
                    )

                    # Trigger overdue alert
                    alert_engine_p19.process_incident_alert(
                        "ACTION_OVERDUE",
                        inc,
                        extra_info=f"Unacknowledged for {int(elapsed/60)} minutes.",
                        force=True
                    )

                    escalated_list.append(inc)

            except Exception as e:
                print(f"Escalation Engine error for {inc_id}: {e}")

        return escalated_list


escalation_engine_p19 = EscalationEngine()

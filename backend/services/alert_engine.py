"""
backend/services/alert_engine.py
=================================
Phase 19 — Resilience Orchestration, Incident Management & Automated Alerting

Alert Engine detecting risk escalation, new incidents, overdue actions, and risk recurrence
with built-in alert deduplication and cooldown management.
"""

import time
from typing import Dict, Any, List, Optional

_ALERT_CACHE: Dict[str, float] = {}
COOLDOWN_SECONDS = 300.0  # 5 minutes cooldown for identical alerts


class AlertEngine:
    """Detects critical conditions and dispatches deduplicated alerts."""

    def should_dispatch(self, alert_key: str, force: bool = False) -> bool:
        """Checks if alert can be dispatched or if it's within cooldown window."""
        if force:
            return True
        now = time.time()
        last_sent = _ALERT_CACHE.get(alert_key, 0.0)
        if (now - last_sent) >= COOLDOWN_SECONDS:
            _ALERT_CACHE[alert_key] = now
            return True
        return False

    def process_incident_alert(
        self, alert_type: str, incident: Dict[str, Any], extra_info: str = None, force: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Processes and constructs an alert for an incident.
        alert_types: NEW_INCIDENT, RISK_ESCALATION, ACTION_OVERDUE, INCIDENT_ESCALATION, RISK_RECURRED, INCIDENT_RESOLVED
        """
        inc_id = incident.get("incident_id", "CG-ALERT")
        site_id = incident.get("site_id", "SITE-001")
        site_name = incident.get("site_name", "Facility")
        eq_id = incident.get("equipment_id", "ASSET")
        sev = incident.get("severity", "HIGH")

        alert_key = f"{alert_type}_{site_id}_{eq_id}_{sev}"
        if not self.should_dispatch(alert_key, force=force):
            return None

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        title_map = {
            "NEW_INCIDENT": f"🚨 NEW INCIDENT: {sev} Risk detected at {site_name}",
            "RISK_ESCALATION": f"⚡ RISK ESCALATION: {eq_id} at {site_name} escalated to {sev}",
            "ACTION_OVERDUE": f"⚠️ ACTION OVERDUE: Response timeframe exceeded for {eq_id} at {site_name}",
            "INCIDENT_ESCALATION": f"🔥 INCIDENT ESCALATED: Unacknowledged risk {inc_id} escalated",
            "RISK_RECURRED": f"🔄 RISK RECURRENCE: Escalated condition re-detected for {eq_id}",
            "INCIDENT_RESOLVED": f"✓ INCIDENT RESOLVED: Incident {inc_id} successfully mitigated"
        }

        title = title_map.get(alert_type, f"ALERT: Infrastructure Risk at {site_name}")
        msg = (
            f"Facility: {site_name} ({site_id}) | Asset: {eq_id} ({incident.get('equipment_type')})\n"
            f"Severity: {sev} | Risk Score: {incident.get('risk_score')}/100 | Priority: {incident.get('priority_score')}/100\n"
            f"Action: {incident.get('recommended_action')}\n"
        )
        if extra_info:
            msg += f"Note: {extra_info}"

        alert_record = {
            "alert_id": f"ALT-{int(time.time() * 1000)}",
            "incident_id": inc_id,
            "alert_type": alert_type,
            "site_id": site_id,
            "site_name": site_name,
            "equipment_id": eq_id,
            "severity": sev,
            "title": title,
            "message": msg,
            "timestamp": now_str,
            "cooldown_applied": True
        }

        # Dispatch via Notification Engine
        from services.notification_engine import notification_engine
        notification_engine.create_notification(
            incident_id=inc_id,
            site_id=site_id,
            recipient_role=incident.get("assigned_team", "Operations"),
            notification_type=alert_type,
            title=title,
            message=msg,
            severity=sev
        )

        return alert_record


alert_engine_p19 = AlertEngine()

"""
backend/services/incident_monitor.py
=====================================
Phase 19 — Resilience Orchestration, Incident Management & Automated Alerting

Incident Monitor providing idempotent multi-facility automated evaluation,
incident creation, alert deduplication, and escalation tracking.
"""

import time
from typing import Dict, Any, List

import state
from services.decision_engine import decision_engine
from services.incident_engine_phase19 import incident_engine_p19
from services.alert_engine import alert_engine_p19
from services.escalation_engine import escalation_engine_p19


class IncidentMonitor:
    """Multi-facility automated incident monitor."""

    def evaluate_all_facilities(self) -> Dict[str, Any]:
        """
        Evaluates weather, prediction, and decision outputs across all registered facilities.
        Idempotent: Auto-creates incidents for critical/urgent priorities, updates existing incidents,
        and triggers alerts/escalations without flooding duplicates.
        """
        all_sites = state.site_registry.get_all_sites(active_only=True)
        new_cnt = 0
        updated_cnt = 0
        alerts_sent = 0

        for site in all_sites:
            site_id = site["site_id"]
            site_name = site["site_name"]

            # 1. Fetch Live Weather Data
            w_norm = state.weather_client_inst.get_current_data(
                location=site.get("city"),
                latitude=site.get("latitude"),
                longitude=site.get("longitude"),
                site_id=site_id
            )
            weather_full = w_norm["data"]

            # 2. Evaluate Decision Engine
            dec_res = decision_engine.evaluate_facility_decisions(site, weather_full)
            decisions = dec_res.get("decisions", [])

            for d in decisions:
                r_score = d.get("risk_score", 0.0)
                p_score = d.get("action_priority_score", 0.0)
                urg_lvl = d.get("urgency_level", "LOW")

                # Auto-create trigger: Priority >= 50.0 or Urgency in CRITICAL/URGENT
                if p_score >= 50.0 or urg_lvl in ["CRITICAL", "URGENT"]:
                    eq_id = d.get("equipment_id")
                    eq_type = d.get("equipment_type")

                    inc, is_new = incident_engine_p19.create_or_update_incident(
                        site_id=site_id,
                        site_name=site_name,
                        equipment_id=eq_id,
                        equipment_type=eq_type,
                        risk_score=r_score,
                        priority_score=p_score,
                        impact_score=d.get("impact_score", 50.0),
                        urgency_score=d.get("urgency_score", 50.0),
                        recommended_action=d.get("action"),
                        reason=d.get("why"),
                        climate_driver=d.get("primary_climate_driver", "HEAT"),
                        decision_confidence=d.get("decision_confidence_pct", 85.0),
                        timeframe=d.get("when_timeframe", "Within 6 Hours")
                    )

                    if is_new:
                        new_cnt += 1
                        # Dispatch initial alert for new incident
                        alert_rec = alert_engine_p19.process_incident_alert("NEW_INCIDENT", inc)
                        if alert_rec:
                            alerts_sent += 1
                    else:
                        updated_cnt += 1

        # 3. Check Escalations for Overdue Actions
        escalated_incidents = escalation_engine_p19.evaluate_escalations()

        return {
            "success": True,
            "evaluated_facilities": len(all_sites),
            "new_incidents_created": new_cnt,
            "incidents_updated": updated_cnt,
            "escalated_incidents_count": len(escalated_incidents),
            "alerts_dispatched": alerts_sent,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }


incident_monitor_p19 = IncidentMonitor()

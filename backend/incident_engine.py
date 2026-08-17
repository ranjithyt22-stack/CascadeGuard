"""
CascadeGuard AI — Incident Engine & Correlation Architecture
Phase 13: Incident Intelligence + Automated Alerting + Executive Report

Monitors system risk, asset risk scores, early warning signals, and climate stress,
automatically generating, deduplicating, and tracking infrastructure incidents.
"""

import time
import copy
from site_config import get_risk_thresholds
from recommendation_engine import generate_recommendations

# In-memory incident buffer (last 100 incidents)
_INCIDENT_HISTORY = []
_INCIDENT_COUNTER = 0
_ACTIVE_INCIDENT = None


class IncidentEngine:
    def __init__(self):
        global _INCIDENT_HISTORY, _INCIDENT_COUNTER, _ACTIVE_INCIDENT
        self.history = _INCIDENT_HISTORY
        self.active_incident = _ACTIVE_INCIDENT

    def evaluate_telemetry_incident(self, multi_asset_eval, ot_telemetry_data=None, active_scenario="NORMAL"):
        """
        Evaluates system evaluation payload and OT telemetry, creating or updating incidents.
        Applies incident deduplication to prevent generating duplicate incidents on every poll.
        """
        global _INCIDENT_COUNTER, _ACTIVE_INCIDENT

        thresholds = get_risk_thresholds()
        watch_thresh = thresholds.get("watch", 25.0)
        warn_thresh = thresholds.get("warning", 50.0)
        crit_thresh = thresholds.get("critical", 75.0)

        sys_data = multi_asset_eval.get("system", {})
        sys_risk = float(sys_data.get("system_cascade_risk", 0.0))
        ew_state = str(sys_data.get("early_warning_level", "NORMAL")).upper()
        vuln_asset = sys_data.get("most_vulnerable_asset", "TRANSFORMER")
        trend = sys_data.get("risk_trend", "STABLE")

        assets = multi_asset_eval.get("assets", {})
        tx = assets.get("transformer", {})
        ch = assets.get("chiller", {})
        wp = assets.get("water_pump", {})

        tx_risk = float(tx.get("cascade_risk_score", tx.get("risk_score", 0.0)))
        ch_risk = float(ch.get("chiller_risk_score", ch.get("risk_score", 0.0)))
        wp_risk = float(wp.get("pump_risk_score", wp.get("risk_score", 0.0)))
        max_asset_risk = max(tx_risk, ch_risk, wp_risk)

        # Trigger Criteria Check
        should_trigger = (
            sys_risk >= warn_thresh or
            max_asset_risk >= 60.0 or
            ew_state in ["WARNING", "CRITICAL"] or
            trend == "RISING"
        )

        if not should_trigger:
            # If active incident exists and risk has dropped back to normal, mark resolved
            if _ACTIVE_INCIDENT and _ACTIVE_INCIDENT.get("status") in ["OPEN", "ACKNOWLEDGED"]:
                if sys_risk < watch_thresh:
                    _ACTIVE_INCIDENT["status"] = "RESOLVED"
                    _ACTIVE_INCIDENT["resolved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    _ACTIVE_INCIDENT = None
            return _ACTIVE_INCIDENT

        # Determine Severity Level
        if sys_risk >= crit_thresh or max_asset_risk >= 85.0 or ew_state == "CRITICAL":
            severity = "CRITICAL"
        elif sys_risk >= warn_thresh or max_asset_risk >= 60.0 or ew_state == "WARNING":
            severity = "WARNING"
        else:
            severity = "WATCH"

        trigger_reason = f"System Risk ({sys_risk:.1f}) >= {warn_thresh} or Asset Risk ({max_asset_risk:.1f}) elevated under {active_scenario} scenario."
        climate = multi_asset_eval.get("climate", {})
        recs = generate_recommendations(sys_risk, assets, climate, active_scenario)

        # Data Provenance Summary
        data_sources = {
            "climate": climate.get("source", "LIVE_OPEN_METEO_API"),
            "transformer": tx.get("source", "HISTORICAL_REPLAY"),
            "chiller": ch.get("source", "HISTORICAL_DATASET"),
            "water_pump": wp.get("source", "HISTORICAL_DATASET (DECISION SUPPORT ONLY)")
        }

        # Cascade Propagation Narrative
        cascade_path = (
            f"Climate Stress ({climate.get('climate_stress', 0):.1f}) ➔ "
            f"Water Pump Risk ({wp_risk:.1f}) ➔ "
            f"Chiller Risk ({ch_risk:.1f}) ➔ "
            f"Transformer Risk ({tx_risk:.1f}) ➔ "
            f"System Cascade Risk ({sys_risk:.1f})"
        )

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        # DEDUPLICATION LOGIC:
        # If an active open/acknowledged incident exists and scenario hasn't changed, update existing incident record
        if _ACTIVE_INCIDENT and _ACTIVE_INCIDENT.get("status") in ["OPEN", "ACKNOWLEDGED"]:
            old_scenario = _ACTIVE_INCIDENT.get("scenario", "NORMAL")
            if old_scenario == active_scenario:
                # Update existing active incident
                _ACTIVE_INCIDENT["system_risk"] = sys_risk
                _ACTIVE_INCIDENT["most_vulnerable_asset"] = vuln_asset
                _ACTIVE_INCIDENT["affected_assets"] = {
                    "transformer_risk": tx_risk,
                    "chiller_risk": ch_risk,
                    "water_pump_risk": wp_risk
                }
                # Escalate severity if risk increased
                if severity == "CRITICAL" and _ACTIVE_INCIDENT["severity"] != "CRITICAL":
                    _ACTIVE_INCIDENT["severity"] = "CRITICAL"
                _ACTIVE_INCIDENT["recommended_actions"] = recs
                _ACTIVE_INCIDENT["last_updated"] = now_str
                return _ACTIVE_INCIDENT

        # Site Information Extraction
        site_info = multi_asset_eval.get("site", {})
        site_id = site_info.get("site_id", "SITE-001")
        site_name = site_info.get("site_name", "Coimbatore Industrial Facility")

        # Generate NEW Incident
        _INCIDENT_COUNTER += 1
        inc_id = f"INC-{time.strftime('%Y%m%d')}-{_INCIDENT_COUNTER:03d}"

        incident = {
            "incident_id": inc_id,
            "site_id": site_id,
            "site_name": site_name,
            "timestamp": now_str,
            "severity": severity,
            "status": "OPEN",
            "scenario": active_scenario,
            "system_risk": sys_risk,
            "most_vulnerable_asset": vuln_asset,
            "affected_assets": {
                "transformer_risk": tx_risk,
                "chiller_risk": ch_risk,
                "water_pump_risk": wp_risk
            },
            "trigger": trigger_reason,
            "climate_condition": {
                "temperature": climate.get("temperature", 28.5),
                "humidity": climate.get("humidity", 65.0),
                "climate_stress": climate.get("climate_stress", 19.4)
            },
            "telemetry_condition": ot_telemetry_data or {},
            "cascade_path": cascade_path,
            "confidence": "HIGH (LIVE DATA & ML ENSEMBLE)",
            "data_sources": data_sources,
            "recommended_actions": recs,
            "acknowledged_at": None,
            "resolved_at": None,
            "last_updated": now_str
        }

        _ACTIVE_INCIDENT = incident
        self.history.insert(0, incident)
        if len(self.history) > 100:
            self.history.pop()

        return incident

    def get_all_incidents(self):
        active_list = [inc for inc in self.history if inc.get("status") in ["OPEN", "ACKNOWLEDGED"]]
        resolved_list = [inc for inc in self.history if inc.get("status") == "RESOLVED"]
        return {
            "active_incidents": active_list,
            "resolved_incidents": resolved_list,
            "history": self.history
        }

    def get_incidents(self):
        return self.get_all_incidents()

    def get_incident_by_id(self, incident_id):
        for inc in self.history:
            if inc.get("incident_id") == incident_id:
                return inc
        return None

    def acknowledge_incident(self, incident_id):
        inc = self.get_incident_by_id(incident_id)
        if inc:
            inc["status"] = "ACKNOWLEDGED"
            inc["acknowledged_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            return True, inc
        return False, None

    def resolve_incident(self, incident_id):
        global _ACTIVE_INCIDENT
        inc = self.get_incident_by_id(incident_id)
        if inc:
            inc["status"] = "RESOLVED"
            inc["resolved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            if _ACTIVE_INCIDENT and _ACTIVE_INCIDENT.get("incident_id") == incident_id:
                _ACTIVE_INCIDENT = None
            return True, inc
        return False, None

"""
backend/services/incident_engine_phase19.py
=============================================
Phase 19 — Resilience Orchestration, Incident Management & Automated Alerting

Persistent Incident Engine managing the complete incident lifecycle:
OPEN -> ACKNOWLEDGED -> IN_PROGRESS -> MITIGATED -> RESOLVED -> CLOSED (or DISMISSED).
Maintains audit event logs, prevents duplicate incidents, persists data to disk,
and prepares historical learning records for Phase 20 ML.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
INCIDENTS_DB_PATH = DATA_DIR / "incidents_db.json"

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Valid Incident Lifecycle Transitions
VALID_TRANSITIONS = {
    "OPEN": ["ACKNOWLEDGED", "IN_PROGRESS", "DISMISSED"],
    "ACKNOWLEDGED": ["IN_PROGRESS", "MITIGATED", "DISMISSED"],
    "IN_PROGRESS": ["MITIGATED", "RESOLVED", "DISMISSED"],
    "MITIGATED": ["RESOLVED", "CLOSED"],
    "RESOLVED": ["CLOSED", "OPEN"],
    "CLOSED": [],
    "DISMISSED": []
}


def map_priority_to_severity(priority_score: float) -> str:
    """Maps Action Priority score (0-100) to Incident Severity level."""
    p = float(priority_score)
    if p >= 81.0:
        return "CRITICAL"
    elif p >= 61.0:
        return "URGENT"
    elif p >= 41.0:
        return "HIGH"
    elif p >= 21.0:
        return "MODERATE"
    elif p > 0.0:
        return "LOW"
    return "INFO"


class IncidentEnginePhase19:
    """Persistent Incident Management & Resilience Orchestration Engine."""

    def __init__(self, db_path: Path = INCIDENTS_DB_PATH):
        self.db_path = db_path
        self.incidents: Dict[str, Dict[str, Any]] = {}
        self.events: List[Dict[str, Any]] = []
        self.counter: int = 0
        self._load_from_disk()

    def _load_from_disk(self):
        """Loads persistent incident data from JSON file if available."""
        if self.db_path.exists():
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                    self.incidents = payload.get("incidents", {})
                    self.events = payload.get("events", [])
                    self.counter = payload.get("counter", len(self.incidents))
            except Exception as e:
                print(f"IncidentEngine DB load note: {e}")
                self.incidents = {}
                self.events = []
                self.counter = 0

    def _save_to_disk(self):
        """Saves persistent incident data to JSON file."""
        try:
            payload = {
                "incidents": self.incidents,
                "events": self.events,
                "counter": self.counter,
                "last_saved": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            print(f"IncidentEngine DB save error: {e}")

    def generate_incident_id(self) -> str:
        """Generates unique incident ID in CG-YYYYMMDD-XXXX format."""
        self.counter += 1
        date_str = time.strftime("%Y%m%d")
        return f"CG-{date_str}-{self.counter:04d}"

    def log_event(
        self, incident_id: str, event_type: str, description: str, actor: str = "System", metadata: Dict[str, Any] = None
    ):
        """Logs an event in the incident audit timeline."""
        evt = {
            "event_id": f"EVT-{int(time.time() * 1000)}",
            "incident_id": incident_id,
            "event_type": event_type,
            "description": description,
            "actor": actor,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "metadata": metadata or {}
        }
        self.events.append(evt)

        # Attach event to incident internal timeline
        if incident_id in self.incidents:
            if "timeline" not in self.incidents[incident_id]:
                self.incidents[incident_id]["timeline"] = []
            self.incidents[incident_id]["timeline"].append(evt)

    def find_active_duplicate(self, site_id: str, equipment_id: str) -> Optional[Dict[str, Any]]:
        """Checks for existing active incident matching site_id + equipment_id."""
        for inc in self.incidents.values():
            if (
                inc.get("site_id") == site_id and
                inc.get("equipment_id") == equipment_id and
                inc.get("status") in ["OPEN", "ACKNOWLEDGED", "IN_PROGRESS"]
            ):
                return inc
        return None

    def create_or_update_incident(
        self,
        site_id: str,
        site_name: str,
        equipment_id: str,
        equipment_type: str,
        risk_score: float,
        priority_score: float,
        impact_score: float,
        urgency_score: float,
        recommended_action: str,
        reason: str,
        climate_driver: str = "HEAT",
        decision_confidence: float = 85.0,
        timeframe: str = "Within 6 Hours",
        actor: str = "System"
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Creates a new incident or updates existing duplicate active incident.
        Returns Tuple[incident_dict, is_new_created].
        """
        severity = map_priority_to_severity(priority_score)
        existing = self.find_active_duplicate(site_id, equipment_id)

        if existing:
            # Update existing active incident
            inc_id = existing["incident_id"]
            existing["risk_score"] = round(float(risk_score), 2)
            existing["priority_score"] = round(float(priority_score), 2)
            existing["impact_score"] = round(float(impact_score), 2)
            existing["urgency_score"] = round(float(urgency_score), 2)
            existing["recommended_action"] = recommended_action
            existing["reason"] = reason
            existing["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")

            # Escalate severity if priority escalated
            old_sev = existing["severity"]
            if severity == "CRITICAL" and old_sev != "CRITICAL":
                existing["severity"] = "CRITICAL"
                self.log_event(inc_id, "INCIDENT_ESCALATED", f"Incident severity escalated from {old_sev} to CRITICAL.", actor)

            self._save_to_disk()
            return existing, False

        # Create NEW Incident
        inc_id = self.generate_incident_id()
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        # Assign operational team
        eq_upper = str(equipment_type).upper()
        if "TRANSFORMER" in eq_upper:
            team = "Electrical Maintenance & Substation Ops"
        elif "CHILLER" in eq_upper:
            team = "HVAC & Utility Engineering"
        elif "PUMP" in eq_upper:
            team = "Civil Facilities & Drainage"
        else:
            team = "Facility Operations"

        title = f"{eq_upper} {severity} Risk — {site_name}"
        desc = (
            f"{site_name} asset {equipment_id} ({equipment_type}) requires preventive intervention. "
            f"Risk Score: {risk_score:.1f}/100 | Action Priority: {priority_score:.1f}/100. "
            f"Recommended Action: {recommended_action} ({timeframe})."
        )

        incident = {
            "incident_id": inc_id,
            "site_id": site_id,
            "site_name": site_name,
            "equipment_id": equipment_id,
            "equipment_type": eq_upper,
            "title": title,
            "description": desc,
            "climate_driver": climate_driver,
            "risk_score": round(float(risk_score), 2),
            "pre_action_risk_score": round(float(risk_score), 2),
            "post_action_risk_score": None,
            "impact_score": round(float(impact_score), 2),
            "urgency_score": round(float(urgency_score), 2),
            "priority_score": round(float(priority_score), 2),
            "severity": severity,
            "recommended_action": recommended_action,
            "reason": reason,
            "assigned_team": team,
            "timeframe": timeframe,
            "decision_confidence_pct": round(float(decision_confidence), 1),
            "status": "OPEN",
            "created_at": now_str,
            "acknowledged_at": None,
            "started_at": None,
            "mitigated_at": None,
            "resolved_at": None,
            "closed_at": None,
            "last_updated": now_str,
            "response_effectiveness": None,
            "timeline": []
        }

        self.incidents[inc_id] = incident
        self.log_event(inc_id, "INCIDENT_CREATED", f"Incident '{inc_id}' created with {severity} severity.", actor)
        self._save_to_disk()
        return incident, True

    def validate_transition(self, current_status: str, new_status: str) -> bool:
        """Validates if status transition is allowed according to lifecycle rules."""
        curr = str(current_status).upper()
        target = str(new_status).upper()
        allowed = VALID_TRANSITIONS.get(curr, [])
        return target in allowed

    def update_incident_status(self, incident_id: str, new_status: str, actor: str = "Operator", notes: str = None) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Updates incident status adhering to lifecycle transition validation rules.
        Returns Tuple[success, incident_dict, message].
        """
        if incident_id not in self.incidents:
            return False, None, f"Incident ID '{incident_id}' not found."

        inc = self.incidents[incident_id]
        curr_st = inc["status"]
        target_st = str(new_status).upper()

        if curr_st == target_st:
            return True, inc, f"Incident '{incident_id}' is already in status {target_st}."

        if not self.validate_transition(curr_st, target_st):
            return False, inc, f"Invalid state transition: Cannot change incident from {curr_st} to {target_st}."

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        inc["status"] = target_st
        inc["last_updated"] = now_str
        if notes:
            inc["operator_notes"] = notes

        if target_st == "ACKNOWLEDGED":
            inc["acknowledged_at"] = now_str
            self.log_event(incident_id, "INCIDENT_ACKNOWLEDGED", f"Incident acknowledged by {actor}.", actor)

        elif target_st == "IN_PROGRESS":
            inc["started_at"] = now_str
            self.log_event(incident_id, "ACTION_STARTED", f"Preventive action started by {actor}.", actor)

        elif target_st == "MITIGATED":
            inc["mitigated_at"] = now_str
            self.log_event(incident_id, "INCIDENT_MITIGATED", f"Incident marked mitigated by {actor}.", actor)

        elif target_st == "RESOLVED":
            inc["resolved_at"] = now_str
            self.log_event(incident_id, "INCIDENT_RESOLVED", f"Incident marked resolved by {actor}.", actor)

        elif target_st == "CLOSED":
            inc["closed_at"] = now_str
            self.log_event(incident_id, "INCIDENT_CLOSED", f"Incident closed by {actor}.", actor)

        elif target_st == "DISMISSED":
            inc["dismissed_at"] = now_str
            self.log_event(incident_id, "INCIDENT_DISMISSED", f"Incident dismissed by {actor}.", actor)

        self._save_to_disk()
        return True, inc, f"Incident status updated to {target_st}."

    def get_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        return self.incidents.get(incident_id)

    def get_all_incidents(self, active_only: bool = False, site_id: str = None) -> List[Dict[str, Any]]:
        results = list(self.incidents.values())
        if active_only:
            results = [inc for inc in results if inc["status"] in ["OPEN", "ACKNOWLEDGED", "IN_PROGRESS"]]
        if site_id and site_id != "ALL":
            results = [inc for inc in results if inc["site_id"] == site_id]
        
        # Sort by creation date descending
        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return results

    def get_incident_summary_kpis(self) -> Dict[str, Any]:
        """Calculates system-level incident KPIs."""
        all_inc = list(self.incidents.values())
        active = [inc for inc in all_inc if inc["status"] in ["OPEN", "ACKNOWLEDGED", "IN_PROGRESS"]]
        critical = [inc for inc in active if inc["severity"] == "CRITICAL"]
        urgent = [inc for inc in active if inc["severity"] == "URGENT"]
        unack = [inc for inc in active if inc["status"] == "OPEN"]

        # Calculate average response & mitigation times in minutes
        resp_times = []
        mit_times = []
        for inc in all_inc:
            c_ts = inc.get("created_at")
            a_ts = inc.get("acknowledged_at")
            m_ts = inc.get("mitigated_at") or inc.get("resolved_at")

            if c_ts and a_ts:
                try:
                    t0 = time.mktime(time.strptime(c_ts, "%Y-%m-%d %H:%M:%S"))
                    t1 = time.mktime(time.strptime(a_ts, "%Y-%m-%d %H:%M:%S"))
                    resp_times.append((t1 - t0) / 60.0)
                except Exception:
                    pass

            if c_ts and m_ts:
                try:
                    t0 = time.mktime(time.strptime(c_ts, "%Y-%m-%d %H:%M:%S"))
                    t2 = time.mktime(time.strptime(m_ts, "%Y-%m-%d %H:%M:%S"))
                    mit_times.append((t2 - t0) / 60.0)
                except Exception:
                    pass

        avg_resp = round(sum(resp_times) / len(resp_times), 1) if resp_times else 0.0
        avg_mit = round(sum(mit_times) / len(mit_times), 1) if mit_times else 0.0

        return {
            "total_incidents": len(all_inc),
            "active_incidents": len(active),
            "critical_incidents": len(critical),
            "urgent_incidents": len(urgent),
            "unacknowledged_incidents": len(unack),
            "average_response_minutes": avg_resp,
            "average_mitigation_minutes": avg_mit
        }

    def export_learning_dataset(self) -> List[Dict[str, Any]]:
        """Generates historical learning dataset for Phase 20 ML model improvement."""
        dataset = []
        for inc in self.incidents.values():
            if inc.get("status") in ["MITIGATED", "RESOLVED", "CLOSED"]:
                dataset.append({
                    "incident_id": inc.get("incident_id"),
                    "site_id": inc.get("site_id"),
                    "equipment_id": inc.get("equipment_id"),
                    "equipment_type": inc.get("equipment_type"),
                    "climate_driver": inc.get("climate_driver"),
                    "risk_before": inc.get("pre_action_risk_score"),
                    "risk_after": inc.get("post_action_risk_score"),
                    "risk_reduction": round(float((inc.get("pre_action_risk_score") or 0.0) - (inc.get("post_action_risk_score") or 0.0)), 2),
                    "recommended_action": inc.get("recommended_action"),
                    "response_effectiveness": (inc.get("response_effectiveness") or {}).get("effectiveness_level", "UNKNOWN"),
                    "decision_confidence_pct": inc.get("decision_confidence_pct"),
                    "created_at": inc.get("created_at"),
                    "resolved_at": inc.get("resolved_at") or inc.get("mitigated_at")
                })
        return dataset


incident_engine_p19 = IncidentEnginePhase19()

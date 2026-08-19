"""
backend/services/decision_engine.py
===================================
Phase 18 — AI-Powered Climate Resilience Decision & Response Engine

Unified Decision Engine combining Impact Assessment, Urgency Evaluation, Recommendation Engine,
Action Priority Scoring, Multi-Timeline Response Plans, Cascading Risk Detection, and Action Status Tracking.
"""

import numpy as np
import time
from typing import Dict, Any, List

from services.impact_engine import impact_engine
from services.urgency_engine import urgency_engine
from services.recommendation_engine_phase18 import recommendation_engine_p18
from services.prediction_engine import prediction_engine


# Centralized Action Priority Configurable Weights
ACTION_PRIORITY_CONFIG = {
    "weights": {
        "risk_severity": 0.35,
        "operational_impact": 0.25,
        "urgency": 0.20,
        "equipment_criticality": 0.15,
        "climate_severity": 0.05
    },
    "levels": {
        "low_max": 20.0,
        "moderate_max": 40.0,
        "high_max": 60.0,
        "urgent_max": 80.0
    }
}

# In-Memory Action Status Tracker
_ACTION_TRACKER: Dict[str, Dict[str, Any]] = {}


def get_action_priority_level(score: float) -> str:
    """Utility mapping 0-100 Action Priority score to category level."""
    s = float(score)
    cfg = ACTION_PRIORITY_CONFIG["levels"]
    if s <= cfg["low_max"]:
        return "LOW"
    elif s <= cfg["moderate_max"]:
        return "MODERATE"
    elif s <= cfg["high_max"]:
        return "HIGH"
    elif s <= cfg["urgent_max"]:
        return "URGENT"
    return "CRITICAL"


class DecisionEngine:
    """Core AI-Assisted Decision & Response Engine."""

    def __init__(self, priority_config: Dict[str, Any] = None):
        self.priority_config = priority_config or ACTION_PRIORITY_CONFIG

    def calculate_action_priority_score(
        self,
        risk_score: float,
        impact_score: float,
        urgency_score: float,
        criticality_score: float,
        climate_stress: float
    ) -> Dict[str, Any]:
        """
        Calculates Action Priority Score (0-100) using configurable weights.
        Formula: 0.35*Risk + 0.25*Impact + 0.20*Urgency + 0.15*Criticality + 0.05*Climate
        """
        weights = self.priority_config["weights"]

        r_part = float(np.clip(risk_score, 0.0, 100.0)) * weights["risk_severity"]
        i_part = float(np.clip(impact_score, 0.0, 100.0)) * weights["operational_impact"]
        u_part = float(np.clip(urgency_score, 0.0, 100.0)) * weights["urgency"]
        c_part = float(np.clip(criticality_score, 0.0, 100.0)) * weights["equipment_criticality"]
        cl_part = float(np.clip(climate_stress, 0.0, 100.0)) * weights["climate_severity"]

        priority_score = r_part + i_part + u_part + c_part + cl_part
        priority_score = float(np.clip(priority_score, 0.0, 100.0))
        round_priority = round(priority_score, 2)
        level = get_action_priority_level(round_priority)

        return {
            "action_priority_score": round_priority,
            "action_priority_level": level,
            "breakdown": {
                "risk_contribution": round(r_part, 2),
                "impact_contribution": round(i_part, 2),
                "urgency_contribution": round(u_part, 2),
                "criticality_contribution": round(c_part, 2),
                "climate_contribution": round(cl_part, 2)
            }
        }

    def detect_cascading_risk(self, equipment_risks: Dict[str, Any], weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detects cross-equipment cascading climate risks (Heat -> Chiller -> Transformer)."""
        tx_risk = equipment_risks.get("transformer", {}).get("risk_score", 0.0)
        ch_risk = equipment_risks.get("chiller", {}).get("risk_score", 0.0)
        wp_risk = equipment_risks.get("water_pump", {}).get("risk_score", 0.0)
        temp = float(weather_data.get("temperature", 28.5))

        cascading_detected = False
        chain_description = "Equipment operating independently within standard thresholds."

        if temp >= 35.0 and ch_risk >= 50.0 and tx_risk >= 50.0:
            cascading_detected = True
            chain_description = "HEAT CASCADE DETECTED: Extreme ambient heat is surging HVAC Chiller cooling load, increasing electrical draw on Power Transformer."
        elif weather_data.get("rain", 0.0) >= 15.0 and wp_risk >= 50.0:
            cascading_detected = True
            chain_description = "MONSOON FLOOD CASCADE DETECTED: Heavy rainfall elevating Water Pump stress and potential basement water ingress risk."

        return {
            "cascading_risk_detected": cascading_detected,
            "chain_description": chain_description,
            "primary_vulnerability": "Transformer & Chiller Coupled Load" if cascading_detected else "None"
        }

    def generate_response_plan(
        self,
        site_data: Dict[str, Any],
        weather_data: Dict[str, Any],
        equipment_risks: Dict[str, Any],
        decisions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generates multi-timeline response plan across:
        NOW, NEXT 2 HOURS, NEXT 6 HOURS, NEXT 24 HOURS, NEXT 3 DAYS.
        """
        site_name = site_data.get("site_name", "Facility")
        
        now_actions = []
        next_2h_actions = []
        next_6h_actions = []
        next_24h_actions = []
        next_3d_actions = []

        for d in decisions:
            priority = d.get("priority", "LOW")
            eq_id = d.get("equipment_id", "Asset")
            act_item = {
                "action_id": d.get("action_id"),
                "equipment_id": eq_id,
                "equipment_type": d.get("equipment_type"),
                "action": d.get("action"),
                "why": d.get("why"),
                "priority": priority,
                "responsible_team": d.get("responsible_team"),
                "status": d.get("status", "PENDING")
            }

            if priority in ["CRITICAL", "URGENT"]:
                now_actions.append(act_item)
                next_2h_actions.append({
                    "action": f"Verify execution of {d.get('action')}",
                    "equipment_id": eq_id,
                    "priority": priority
                })
            elif priority == "HIGH":
                next_2h_actions.append(act_item)
                next_6h_actions.append({
                    "action": f"Inspect secondary parameters for {eq_id}",
                    "equipment_id": eq_id,
                    "priority": "HIGH"
                })
            elif priority == "MODERATE":
                next_6h_actions.append(act_item)
                next_24h_actions.append({
                    "action": f"Re-evaluate risk trend for {eq_id}",
                    "equipment_id": eq_id,
                    "priority": "MODERATE"
                })
            else:
                next_24h_actions.append(act_item)
                next_3d_actions.append({
                    "action": f"Perform routine preventive maintenance on {eq_id}",
                    "equipment_id": eq_id,
                    "priority": "LOW"
                })

        return {
            "facility_name": site_name,
            "timelines": {
                "now": now_actions if now_actions else [{"action": "Maintain routine automated monitoring", "priority": "LOW"}],
                "next_2_hours": next_2h_actions if next_2h_actions else [{"action": "Review telemetry trends", "priority": "LOW"}],
                "next_6_hours": next_6h_actions if next_6h_actions else [{"action": "Check Open-Meteo forecast update", "priority": "LOW"}],
                "next_24_hours": next_24h_actions if next_24h_actions else [{"action": "Conduct daily shift equipment walkaround", "priority": "LOW"}],
                "next_3_days": next_3d_actions if next_3d_actions else [{"action": "Weekly preventive maintenance schedule review", "priority": "LOW"}]
            }
        }

    def evaluate_facility_decisions(
        self, site_data: Dict[str, Any], weather_full: Dict[str, Any], telemetry_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Evaluates decisions, action priorities, and response plans for a facility."""
        site_id = site_data.get("site_id", "SITE-001")
        site_name = site_data.get("site_name", "Industrial Facility")
        city = site_data.get("city", "Coimbatore")

        # 1. Fetch Phase 17 Predictive Evaluation
        pred_res = prediction_engine.predict_facility_risk(site_data, weather_full, telemetry_data)
        eq_risks = pred_res["equipment"]
        overall_risk = pred_res["overall_facility_risk"]
        climate_stress = pred_res["climate_risk"]
        trend_info = pred_res["trend_analysis"]

        decisions_list = []
        all_priority_scores = []

        # 2. Evaluate Equipment Decisions
        for eq_type, eq_data in eq_risks.items():
            eq_id = eq_data.get("equipment_id", f"{eq_type.upper()}-{site_id}")
            r_score = eq_data.get("risk_score", 0.0)

            # Impact Assessment
            imp_res = impact_engine.calculate_equipment_impact(eq_type, r_score, climate_stress)

            # Urgency Assessment
            urg_res = urgency_engine.calculate_urgency(
                r_score,
                forecast_trend=trend_info.get("trend"),
                trend_delta_24h=trend_info.get("trend_delta_24h"),
                peak_risk_24h=trend_info.get("peak_risk_24h")
            )

            # Action Recommendation
            rec_res = recommendation_engine_p18.generate_action_decision(
                site_name, eq_id, eq_type, r_score, weather_full, imp_res, urg_res
            )

            # Action Priority Score
            prio_res = self.calculate_action_priority_score(
                r_score,
                imp_res["impact_score"],
                urg_res["urgency_score"],
                imp_res["criticality_score"],
                climate_stress
            )
            all_priority_scores.append(prio_res["action_priority_score"])

            # Action Tracker ID & Persistence
            action_id = f"ACT-{site_id}-{eq_type.upper()}"
            existing_track = _ACTION_TRACKER.get(action_id, {})
            status = existing_track.get("status", "PENDING")

            dec_item = {
                "action_id": action_id,
                "site_id": site_id,
                "site_name": site_name,
                "equipment_id": eq_id,
                "equipment_type": eq_type.upper(),
                "risk_score": r_score,
                "impact_score": imp_res["impact_score"],
                "impact_level": imp_res["impact_level"],
                "urgency_score": urg_res["urgency_score"],
                "urgency_level": urg_res["urgency_level"],
                "action_priority_score": prio_res["action_priority_score"],
                "action_priority_level": prio_res["action_priority_level"],
                "priority": rec_res["priority"],
                "action": rec_res["action"],
                "why": rec_res["why"],
                "when_timeframe": rec_res["when_timeframe"],
                "expected_benefit": rec_res["expected_benefit"],
                "responsible_team": rec_res["responsible_team"],
                "decision_confidence_pct": rec_res["decision_confidence_pct"],
                "confidence_level": rec_res["confidence_level"],
                "status": status,
                "acknowledged_at": existing_track.get("acknowledged_at")
            }

            # Update Tracker
            _ACTION_TRACKER[action_id] = {
                "action_id": action_id,
                "site_id": site_id,
                "equipment_id": eq_id,
                "equipment_type": eq_type.upper(),
                "risk_score": r_score,
                "priority_score": prio_res["action_priority_score"],
                "action": rec_res["action"],
                "why": rec_res["why"],
                "status": status,
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }

            decisions_list.append(dec_item)

        # Sort decisions by action_priority_score descending
        decisions_list.sort(key=lambda d: d["action_priority_score"], reverse=True)

        # Top Priority Action
        top_action = decisions_list[0] if decisions_list else None

        # Cascading Risk Analysis
        cascade_info = self.detect_cascading_risk(eq_risks, weather_full)

        # Multi-Timeline Response Plan
        response_plan = self.generate_response_plan(site_data, weather_full, eq_risks, decisions_list)

        facility_priority_score = max(all_priority_scores) if all_priority_scores else overall_risk

        return {
            "site_id": site_id,
            "site_name": site_name,
            "city": city,
            "overall_risk": overall_risk,
            "facility_priority_score": facility_priority_score,
            "facility_priority_level": get_action_priority_level(facility_priority_score),
            "top_action": top_action,
            "decisions": decisions_list,
            "response_plan": response_plan,
            "cascading_risk": cascade_info,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

    def get_action_tracker(self) -> Dict[str, Dict[str, Any]]:
        return _ACTION_TRACKER

    def update_action_status(self, action_id: str, new_status: str) -> bool:
        if action_id in _ACTION_TRACKER:
            _ACTION_TRACKER[action_id]["status"] = str(new_status).upper()
            _ACTION_TRACKER[action_id]["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            if new_status.upper() == "ACKNOWLEDGED":
                _ACTION_TRACKER[action_id]["acknowledged_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            return True
        return False


decision_engine = DecisionEngine()

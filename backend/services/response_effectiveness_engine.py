"""
backend/services/response_effectiveness_engine.py
==================================================
Phase 19 — Resilience Orchestration, Incident Management & Automated Alerting

Response Effectiveness Engine re-evaluating risk post-action completion, comparing pre-action vs post-action
risk scores, and computing observed response effectiveness without unproven causal claims.
"""

import numpy as np
import time
from typing import Dict, Any, Optional

import state
from services.incident_engine_phase19 import incident_engine_p19
from services.prediction_engine import prediction_engine


class ResponseEffectivenessEngine:
    """Evaluates risk reduction and response effectiveness following operator action completion."""

    def evaluate_response_effectiveness(
        self, incident_id: str, operator_notes: str = None
    ) -> Dict[str, Any]:
        """
        Re-evaluates facility risk after operator completes preventive action,
        calculates observed risk reduction, and updates incident status to MITIGATED.
        """
        inc = incident_engine_p19.get_incident(incident_id)
        if not inc:
            return {"success": False, "error": f"Incident ID '{incident_id}' not found."}

        site_id = inc["site_id"]
        site = state.site_registry.get_site(site_id)
        if not site:
            return {"success": False, "error": f"Site ID '{site_id}' not found in registry."}

        # 1. Retrieve Pre-Action Risk Score
        pre_risk = float(inc.get("pre_action_risk_score", inc.get("risk_score", 50.0)))

        # 2. Fetch Latest Weather & Re-evaluate Risk via Prediction Engine
        w_norm = state.weather_client_inst.get_current_data(
            location=site.get("city"),
            latitude=site.get("latitude"),
            longitude=site.get("longitude"),
            site_id=site_id
        )
        weather_full = w_norm["data"]
        pred_res = prediction_engine.predict_facility_risk(site, weather_full)

        # Retrieve specific equipment risk or overall risk
        eq_type = str(inc.get("equipment_type", "TRANSFORMER")).lower()
        if "transformer" in eq_type:
            post_risk = float(pred_res["equipment"]["transformer"]["risk_score"])
        elif "chiller" in eq_type:
            post_risk = float(pred_res["equipment"]["chiller"]["risk_score"])
        elif "pump" in eq_type:
            post_risk = float(pred_res["equipment"]["water_pump"]["risk_score"])
        else:
            post_risk = float(pred_res["overall_facility_risk"])

        post_risk = round(float(np.clip(post_risk, 0.0, 100.0)), 2)

        # 3. Calculate Observed Risk Reduction
        risk_reduction = round(pre_risk - post_risk, 2)

        # 4. Classify Effectiveness Level
        if risk_reduction >= 20.0:
            effectiveness_level = "EFFECTIVE"
            desc = f"Significant observed risk reduction (-{risk_reduction} pts) following preventive operator action."
        elif risk_reduction >= 5.0:
            effectiveness_level = "PARTIALLY_EFFECTIVE"
            desc = f"Moderate observed risk reduction (-{risk_reduction} pts). Continued telemetry monitoring recommended."
        else:
            effectiveness_level = "INEFFECTIVE"
            desc = f"Minimal observed risk reduction ({risk_reduction} pts). Secondary technical inspection advised."

        effectiveness_data = {
            "incident_id": incident_id,
            "site_id": site_id,
            "equipment_id": inc.get("equipment_id"),
            "pre_action_risk_score": pre_risk,
            "post_action_risk_score": post_risk,
            "observed_risk_reduction_pts": risk_reduction,
            "effectiveness_level": effectiveness_level,
            "description": desc,
            "operator_notes": operator_notes or "Action completed by operator.",
            "evaluated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        # Update Incident Record
        inc["post_action_risk_score"] = post_risk
        inc["response_effectiveness"] = effectiveness_data
        inc["status"] = "MITIGATED"
        inc["mitigated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        inc["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")

        # Log Audit Events
        incident_engine_p19.log_event(
            incident_id,
            "ACTION_COMPLETED",
            f"Action completed. Notes: {operator_notes or 'None'}",
            actor="Operator"
        )
        incident_engine_p19.log_event(
            incident_id,
            "RISK_RECALCULATED",
            f"Risk re-evaluated from {pre_risk} to {post_risk} (Reduction: {risk_reduction} pts). Effectiveness: {effectiveness_level}.",
            actor="ResponseEffectivenessEngine"
        )
        incident_engine_p19.log_event(
            incident_id,
            "INCIDENT_MITIGATED",
            f"Incident marked MITIGATED following effective risk reduction.",
            actor="System"
        )

        incident_engine_p19._save_to_disk()

        return {
            "success": True,
            "incident": inc,
            "effectiveness": effectiveness_data
        }


response_effectiveness_engine = ResponseEffectivenessEngine()

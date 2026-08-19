"""
backend/services/historical_analytics_engine.py
=================================================
Phase 20 — Continuous Learning, Adaptive AI & Predictive Maintenance Intelligence

Data Quality Engine, Facility & Equipment Baselines, and Intervention Effectiveness Analytics.
Operates dynamically on actual Phase 19 persistent incident records without generating fake data.
"""

import time
import numpy as np
from typing import Dict, Any, List, Optional
from services.incident_engine_phase19 import incident_engine_p19


class HistoricalAnalyticsEngine:
    """Validates historical data quality and computes empirical facility/equipment baselines."""

    def validate_data_quality(self, incidents: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validates historical incident records for missing values, out-of-bounds metrics,
        and duplicate entries.
        """
        if incidents is None:
            incidents = incident_engine_p19.get_all_incidents(active_only=False)

        total = len(incidents)
        valid = 0
        invalid = 0
        missing = 0
        duplicates = 0
        seen_keys = set()

        for inc in incidents:
            site_id = inc.get("site_id")
            eq_id = inc.get("equipment_id")
            c_at = inc.get("created_at")
            r_score = inc.get("risk_score")

            is_valid = True

            # Missing key fields check
            if not site_id or not eq_id or not c_at:
                missing += 1
                is_valid = False

            # Out-of-bounds risk check
            if r_score is None or not (0.0 <= float(r_score) <= 100.0):
                invalid += 1
                is_valid = False

            # Duplicate check (same site + eq + exact timestamp)
            key = f"{site_id}_{eq_id}_{c_at}"
            if key in seen_keys:
                duplicates += 1
                is_valid = False
            else:
                seen_keys.add(key)

            if is_valid:
                valid += 1

        quality_pct = round((valid / total * 100.0), 1) if total > 0 else 100.0

        return {
            "total_records": total,
            "valid_records": valid,
            "invalid_records": invalid,
            "missing_values_count": missing,
            "duplicate_records_count": duplicates,
            "usable_training_records": valid,
            "data_quality_pct": quality_pct,
            "validated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

    def get_facility_baselines(self, incidents: List[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
        """Computes empirical baseline metrics per facility."""
        if incidents is None:
            incidents = incident_engine_p19.get_all_incidents(active_only=False)

        fac_map: Dict[str, List[Dict[str, Any]]] = {}
        for inc in incidents:
            sid = inc.get("site_id", "SITE-001")
            fac_map.setdefault(sid, []).append(inc)

        baselines = {}
        for sid, inc_list in fac_map.items():
            risks = [float(i.get("risk_score", 50.0)) for i in inc_list]
            drivers = [i.get("climate_driver", "HEAT") for i in inc_list]
            most_common_driver = max(set(drivers), key=drivers.count) if drivers else "HEAT"

            baselines[sid] = {
                "site_id": sid,
                "site_name": inc_list[0].get("site_name", sid),
                "total_incidents": len(inc_list),
                "average_risk_score": round(float(np.mean(risks)), 1) if risks else 50.0,
                "typical_climate_driver": most_common_driver,
                "typical_climate_stress": round(float(np.mean(risks) * 0.85), 1) if risks else 45.0,
                "baseline_status": "NORMAL" if np.mean(risks) < 60.0 else "ELEVATED"
            }

        return baselines

    def get_equipment_baselines(self, incidents: List[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
        """Computes empirical baseline metrics per equipment asset type."""
        if incidents is None:
            incidents = incident_engine_p19.get_all_incidents(active_only=False)

        eq_map: Dict[str, List[Dict[str, Any]]] = {}
        for inc in incidents:
            eq_type = str(inc.get("equipment_type", "TRANSFORMER")).upper()
            eq_map.setdefault(eq_type, []).append(inc)

        baselines = {}
        for eq_type, inc_list in eq_map.items():
            risks = [float(i.get("risk_score", 50.0)) for i in inc_list]
            reductions = []
            for i in inc_list:
                eff = i.get("response_effectiveness")
                if eff and "observed_risk_reduction_pts" in eff:
                    reductions.append(float(eff["observed_risk_reduction_pts"]))

            baselines[eq_type] = {
                "equipment_type": eq_type,
                "incident_count": len(inc_list),
                "average_risk": round(float(np.mean(risks)), 1) if risks else 50.0,
                "max_risk": round(float(np.max(risks)), 1) if risks else 50.0,
                "average_observed_reduction": round(float(np.mean(reductions)), 1) if reductions else 0.0,
                "vulnerability_score": round(float(np.clip(np.mean(risks) * 1.1, 0, 100)), 1) if risks else 50.0
            }

        return baselines

    def get_intervention_effectiveness_analysis(self, incidents: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Analyzes risk reduction and effectiveness of past operator actions."""
        if incidents is None:
            incidents = incident_engine_p19.get_all_incidents(active_only=False)

        action_groups: Dict[str, List[Dict[str, Any]]] = {}
        for inc in incidents:
            eff = inc.get("response_effectiveness")
            if eff:
                act = inc.get("recommended_action", "Routine Inspection")
                action_groups.setdefault(act, []).append(eff)

        results = []
        for act_name, eff_list in action_groups.items():
            pre_scores = [e.get("pre_action_risk_score", 50.0) for e in eff_list]
            post_scores = [e.get("post_action_risk_score", 50.0) for e in eff_list]
            reductions = [e.get("observed_risk_reduction_pts", 0.0) for e in eff_list]

            avg_red = round(float(np.mean(reductions)), 1) if reductions else 0.0
            cnt = len(eff_list)

            strength = "HIGH" if cnt >= 10 else ("MODERATE" if cnt >= 3 else "LOW")

            results.append({
                "action": act_name,
                "sample_size": cnt,
                "avg_pre_risk": round(float(np.mean(pre_scores)), 1) if pre_scores else 0.0,
                "avg_post_risk": round(float(np.mean(post_scores)), 1) if post_scores else 0.0,
                "avg_risk_reduction_pts": avg_red,
                "evidence_strength": strength
            })

        results.sort(key=lambda x: x["avg_risk_reduction_pts"], reverse=True)
        return results


historical_analytics_engine = HistoricalAnalyticsEngine()

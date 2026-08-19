"""
backend/services/optimization_engine.py
========================================
Phase 22 — Resilience Optimization & Prescriptive Action Planner Engine

Physics-backed multi-attribute prescriptive optimizer that evaluates candidate intervention plans
against Digital Twin simulations, ranks options via a weighted multi-objective scoring function,
generates explainable plan rationale and trade-off matrices, conducts sensitivity/robustness analysis,
and manages human-approval workflows for operational resilience planning.
"""

import time
import numpy as np
from typing import Dict, Any, List, Optional

import state
from services.digital_twin_engine import digital_twin_engine
from services.intervention_library import intervention_library
from services.recommendation_learning_engine import recommendation_learning_engine


class OptimizationEngine:
    """Prescriptive Optimization Engine for climate resilience action planning."""

    def __init__(self):
        # Configurable multi-attribute objective weights
        self.WEIGHT_RISK_REDUCTION = 0.35
        self.WEIGHT_FEASIBILITY = 0.25
        self.WEIGHT_RESPONSE_SPEED = 0.20
        self.WEIGHT_RESOURCE_EFFICIENCY = 0.10
        self.WEIGHT_HISTORICAL_EVIDENCE = 0.10

        # Audit log storage
        self._optimization_registry: Dict[str, Dict[str, Any]] = {}

    def classify_plan_score(self, score: float) -> str:
        """Classifies objective plan score (0 - 100)."""
        if score >= 81.0:
            return "OPTIMAL"
        elif score >= 61.0:
            return "STRONG"
        elif score >= 41.0:
            return "ACCEPTABLE"
        elif score >= 21.0:
            return "LIMITED"
        else:
            return "POOR"

    def compute_plan_objective_score(
        self,
        risk_reduction: float,
        disruption: str,
        response_time_min: int,
        resource_level: str,
        evidence_strength: str
    ) -> float:
        """Calculates multi-attribute objective score (0 - 100)."""
        # 1. Risk Reduction Score (0 - 100)
        norm_risk_red = float(np.clip(risk_reduction * 2.0, 0.0, 100.0))

        # 2. Operational Feasibility Score (0 - 100)
        feasibility_map = {"NONE": 100.0, "LOW": 85.0, "MEDIUM": 65.0, "HIGH": 40.0}
        norm_feasibility = feasibility_map.get(disruption.upper(), 60.0)

        # 3. Response Speed Score (0 - 100)
        norm_speed = float(np.clip(100.0 - (response_time_min / 90.0) * 100.0, 0.0, 100.0))

        # 4. Resource Efficiency Score (0 - 100)
        resource_map = {"LOW": 100.0, "MEDIUM": 70.0, "HIGH": 40.0}
        norm_resource = resource_map.get(resource_level.upper(), 60.0)

        # 5. Historical Evidence Score (0 - 100)
        evidence_map = {"HIGH": 100.0, "MODERATE": 70.0, "LOW": 40.0, "INSUFFICIENT DATA": 50.0}
        norm_evidence = evidence_map.get(evidence_strength.upper(), 50.0)

        # Weighted Sum
        score = (
            self.WEIGHT_RISK_REDUCTION * norm_risk_red +
            self.WEIGHT_FEASIBILITY * norm_feasibility +
            self.WEIGHT_RESPONSE_SPEED * norm_speed +
            self.WEIGHT_RESOURCE_EFFICIENCY * norm_resource +
            self.WEIGHT_HISTORICAL_EVIDENCE * norm_evidence
        )
        return round(float(np.clip(score, 0.0, 100.0)), 1)

    def project_asset_mitigation(
        self,
        site_id: str,
        asset_type: str,
        baseline_risk: float,
        scenario_inputs: Dict[str, Any],
        recommended_action: str = ""
    ) -> Dict[str, Any]:
        """Model one recommendation against the selected asset's current ML risk.

        The intervention effect is calculated by the existing Digital Twin: the
        difference between its no-action and intervention simulations is applied
        to the ML risk baseline supplied by the predictive-risk engine.  This
        keeps the displayed baseline asset-specific while avoiding a fabricated
        fixed percentage reduction.
        """
        normalized_asset = str(asset_type or "").upper().replace(" ", "_")
        if normalized_asset not in {"TRANSFORMER", "CHILLER", "WATER_PUMP"}:
            raise ValueError("Mitigation model not available for this asset type.")

        action_words = set(str(recommended_action).upper().replace("-", " ").split())
        candidates = [
            s for s in intervention_library.get_all_strategies()
            if normalized_asset in s.get("affected_equipment", [])
        ]
        if not candidates:
            raise ValueError("Mitigation model not available for this asset type.")

        # Select an existing intervention-library strategy using the actual
        # recommendation text, never a frontend-provided effectiveness value.
        def strategy_match_score(strategy: Dict[str, Any]) -> int:
            strategy_words = set(
                (strategy.get("name", "") + " " + strategy.get("description", "") + " " + strategy.get("risk_effect", ""))
                .upper().replace("-", " ").split()
            )
            return len(action_words & strategy_words)

        no_action = intervention_library.get_strategy("NO_ACTION")
        low_risk_action = any(word in action_words for word in {"ROUTINE", "NORMAL", "MAINTAIN", "CONTINUE", "MONITOR"})
        strategy = no_action if low_risk_action else max(candidates, key=strategy_match_score)
        if strategy is no_action:
            strategy = no_action

        base_inputs = dict(scenario_inputs)
        baseline = float(np.clip(baseline_risk, 0.0, 100.0))
        unmitigated = digital_twin_engine.simulate_digital_twin_lightweight(base_inputs, baseline)
        modified_inputs = dict(base_inputs)
        strategy_id = strategy["id"]
        if strategy_id == "PRE_COOLING":
            modified_inputs["temperature"] = max(10.0, float(base_inputs.get("temperature", 38.0)) - 4.0)
            modified_inputs["chiller_capacity"] = min(100.0, float(base_inputs.get("chiller_capacity", 100.0)) + 20.0)
        elif strategy_id == "LOAD_REDUCTION":
            modified_inputs["transformer_load"] = max(0.0, float(base_inputs.get("transformer_load", 85.0)) - 20.0)
        elif strategy_id == "COOLING_IMPROVEMENT":
            modified_inputs["transformer_cooling"] = min(100.0, float(base_inputs.get("transformer_cooling", 100.0)) + 25.0)
        elif strategy_id == "CHILLER_RECOVERY":
            modified_inputs["chiller_capacity"] = min(100.0, float(base_inputs.get("chiller_capacity", 100.0)) + 25.0)
        elif strategy_id in {"PUMP_FLOW_RECOVERY", "WATER_PUMP_PREPARATION"}:
            modified_inputs["pump_flow"] = min(120.0, float(base_inputs.get("pump_flow", 100.0)) + (25.0 if strategy_id == "PUMP_FLOW_RECOVERY" else 15.0))
        elif strategy_id == "LOAD_AND_PRECOOL":
            modified_inputs["temperature"] = max(10.0, float(base_inputs.get("temperature", 38.0)) - 4.0)
            modified_inputs["transformer_load"] = max(0.0, float(base_inputs.get("transformer_load", 85.0)) - 20.0)
        elif strategy_id == "COOLING_AND_CHILLER_RECOVERY":
            modified_inputs["transformer_cooling"] = min(100.0, float(base_inputs.get("transformer_cooling", 100.0)) + 25.0)
            modified_inputs["chiller_capacity"] = min(100.0, float(base_inputs.get("chiller_capacity", 100.0)) + 25.0)
        elif strategy_id == "COMBINED_RESILIENCE_PLAN":
            modified_inputs["temperature"] = max(10.0, float(base_inputs.get("temperature", 38.0)) - 4.0)
            modified_inputs["transformer_load"] = max(0.0, float(base_inputs.get("transformer_load", 85.0)) - 20.0)
            modified_inputs["transformer_cooling"] = min(100.0, float(base_inputs.get("transformer_cooling", 100.0)) + 25.0)
            modified_inputs["chiller_capacity"] = min(100.0, float(base_inputs.get("chiller_capacity", 100.0)) + 25.0)

        mitigated = digital_twin_engine.simulate_digital_twin_lightweight(modified_inputs, baseline)
        modelled_change = round(float(unmitigated["system_risk"] - mitigated["system_risk"]), 1)
        projected_risk = round(float(np.clip(baseline - modelled_change, 0.0, 100.0)), 1)
        risk_change = round(projected_risk - baseline, 1)
        reduction = round(max(0.0, baseline - projected_risk), 1)
        objective_score = self.compute_plan_objective_score(
            reduction, strategy["operational_disruption"], strategy["response_time_minutes"],
            strategy["resource_level"], "INSUFFICIENT DATA"
        )
        if reduction >= 10.0:
            status = "RISK REDUCED"
        elif reduction > 0.0:
            status = "RISK PARTIALLY REDUCED"
        elif strategy_id == "NO_ACTION":
            status = "NO SIGNIFICANT PROJECTED CHANGE"
        else:
            status = "LIMITED MITIGATION EFFECT"

        return {
            "baseline_risk": round(baseline, 1),
            "projected_risk": projected_risk,
            "risk_change": risk_change,
            "risk_reduction_points": reduction,
            "strategy_id": strategy_id,
            "strategy_name": strategy["name"],
            "strategy_description": strategy["description"],
            "response_time_minutes": strategy["response_time_minutes"],
            "objective_score": objective_score,
            "status": status,
            "simulation_mode": "DIGITAL_TWIN"
        }

    def optimize_response(self, site_id: str, scenario_inputs: Dict[str, Any], skip_robustness: bool = False) -> Dict[str, Any]:
        """
        Executes prescriptive optimization across candidate intervention plans.
        """

        site = state.site_registry.get_site(site_id)
        site_name = site["site_name"] if site else f"Facility {site_id}"

        # 1. Run Baseline Digital Twin Simulation
        base_sim = digital_twin_engine.simulate_digital_twin(site_id, scenario_inputs)
        baseline_risk = base_sim["baseline"]["system_risk"]
        unmitigated_risk = base_sim["scenario"]["system_risk"]
        unmitigated_resilience = base_sim["scenario"]["resilience_score"]

        # 2. Evaluate Candidate Intervention Plans
        all_strategies = intervention_library.get_all_strategies()
        candidate_plans = []

        for strat in all_strategies:
            strat_id = strat["id"]

            # Map strategy parameters into Digital Twin inputs
            mod_inputs = dict(scenario_inputs)
            if strat_id == "PRE_COOLING":
                mod_inputs["temperature"] = max(10.0, float(scenario_inputs.get("temperature", 38.0)) - 4.0)
                mod_inputs["chiller_capacity"] = min(100.0, float(scenario_inputs.get("chiller_capacity", 100.0)) + 20.0)
            elif strat_id == "LOAD_REDUCTION":
                mod_inputs["transformer_load"] = max(0.0, float(scenario_inputs.get("transformer_load", 85.0)) - 20.0)
            elif strat_id == "COOLING_IMPROVEMENT":
                mod_inputs["transformer_cooling"] = min(100.0, float(scenario_inputs.get("transformer_cooling", 100.0)) + 25.0)
            elif strat_id == "CHILLER_RECOVERY":
                mod_inputs["chiller_capacity"] = min(100.0, float(scenario_inputs.get("chiller_capacity", 100.0)) + 25.0)
            elif strat_id == "PUMP_FLOW_RECOVERY":
                mod_inputs["pump_flow"] = min(120.0, float(scenario_inputs.get("pump_flow", 100.0)) + 25.0)
            elif strat_id == "LOAD_AND_PRECOOL":
                mod_inputs["temperature"] = max(10.0, float(scenario_inputs.get("temperature", 38.0)) - 4.0)
                mod_inputs["transformer_load"] = max(0.0, float(scenario_inputs.get("transformer_load", 85.0)) - 20.0)
            elif strat_id == "COOLING_AND_CHILLER_RECOVERY":
                mod_inputs["transformer_cooling"] = min(100.0, float(scenario_inputs.get("transformer_cooling", 100.0)) + 25.0)
                mod_inputs["chiller_capacity"] = min(100.0, float(scenario_inputs.get("chiller_capacity", 100.0)) + 25.0)
            elif strat_id == "WATER_PUMP_PREPARATION":
                mod_inputs["pump_flow"] = min(120.0, float(scenario_inputs.get("pump_flow", 100.0)) + 15.0)
            elif strat_id == "COMBINED_RESILIENCE_PLAN":
                mod_inputs["temperature"] = max(10.0, float(scenario_inputs.get("temperature", 38.0)) - 4.0)
                mod_inputs["transformer_load"] = max(0.0, float(scenario_inputs.get("transformer_load", 85.0)) - 20.0)
                mod_inputs["transformer_cooling"] = min(100.0, float(scenario_inputs.get("transformer_cooling", 100.0)) + 25.0)
                mod_inputs["chiller_capacity"] = min(100.0, float(scenario_inputs.get("chiller_capacity", 100.0)) + 25.0)

            # Lightweight Digital Twin evaluation
            dt_res = digital_twin_engine.simulate_digital_twin_lightweight(mod_inputs, baseline_risk)
            sim_risk = dt_res["system_risk"]
            sim_resilience = dt_res["resilience_score"]
            risk_red = round(max(0.0, unmitigated_risk - sim_risk), 1)

            # Historical Evidence
            learned_recs = recommendation_learning_engine.get_learned_recommendations("HEAT", "TRANSFORMER")
            if learned_recs and isinstance(learned_recs, list) and len(learned_recs) > 0:
                first_rec = learned_recs[0]
                evidence_str = first_rec.get("historical_evidence_strength", first_rec.get("evidence_strength", "INSUFFICIENT DATA"))
            else:
                evidence_str = "INSUFFICIENT DATA"

            # Compute Objective Score
            obj_score = self.compute_plan_objective_score(
                risk_red,
                strat["operational_disruption"],
                strat["response_time_minutes"],
                strat["resource_level"],
                evidence_str
            )
            classification = self.classify_plan_score(obj_score)

            candidate_plans.append({
                "plan_id": f"PLAN-{strat_id}",
                "strategy_id": strat_id,
                "strategy_name": strat["name"],
                "description": strat["description"],
                "affected_equipment": strat["affected_equipment"],
                "simulated_system_risk": sim_risk,
                "simulated_resilience_score": sim_resilience,
                "risk_reduction_pts": risk_red,
                "operational_disruption": strat["operational_disruption"],
                "response_time_minutes": strat["response_time_minutes"],
                "resource_level": strat["resource_level"],
                "historical_evidence": evidence_str,
                "objective_score": obj_score,
                "score_classification": classification,
                "safety_notes": strat["safety_notes"]
            })

        # Sort plans by objective score descending
        candidate_plans.sort(key=lambda x: x["objective_score"], reverse=True)

        # 3. Identify Distinct Plan Selections
        rec_plan = candidate_plans[0]
        second_plan = candidate_plans[1] if len(candidate_plans) > 1 else candidate_plans[0]

        # Lowest Disruption Plan
        low_disrupt_plans = [p for p in candidate_plans if p["operational_disruption"] in ["NONE", "LOW"]]
        lowest_disruption_plan = low_disrupt_plans[0] if low_disrupt_plans else candidate_plans[-1]

        # Maximum Risk Reduction Plan
        max_risk_plan = max(candidate_plans, key=lambda x: x["risk_reduction_pts"])

        # 4. Generate Explainable Rationale & Action Plan Timeline
        rationale = (
            f"The {rec_plan['strategy_name']} achieved the highest objective score ({rec_plan['objective_score']}/100 - {rec_plan['score_classification']}). "
            f"It delivers a simulated risk reduction of {rec_plan['risk_reduction_pts']} points (lowering system risk from {unmitigated_risk} to {rec_plan['simulated_system_risk']}) "
            f"while maintaining manageable operational disruption ({rec_plan['operational_disruption']}) within an estimated response time of {rec_plan['response_time_minutes']} minutes."
        )

        action_timeline = [
            {"phase": "NOW", "time": "Immediate", "action": "Dispatch shift engineer to verify digital twin parameters and authorize plan."},
            {"phase": "WITHIN 30 MINUTES", "time": f"T+{min(30, rec_plan['response_time_minutes'])}m", "action": f"Execute initial protocol for {rec_plan['strategy_name']}."},
            {"phase": "WITHIN 1 HOUR", "time": "T+60m", "action": "Verify transformer winding temperatures and HVAC chiller discharge pressure."},
            {"phase": "NEXT 6 HOURS", "time": "T+6h", "action": "Monitor thermal stress accumulation and log post-action risk score."},
            {"phase": "NEXT 24 HOURS", "time": "T+24h", "action": "Review operational recovery outcomes and export logs to Phase 20 learning database."}
        ]

        # 5. Conduct Sensitivity & Robustness Analysis
        sensitivity = self.calculate_sensitivity(site_id, scenario_inputs)
        if not skip_robustness:
            robustness = self.calculate_robustness(site_id, scenario_inputs, rec_plan["strategy_id"])
        else:
            robustness = {"is_robust": True, "status_badge": "ROBUST RECOMMENDATION", "explanation": "Sub-optimization robustness evaluation."}

        # 6. Create Audit Record
        opt_id = f"OPT-{int(time.time()*1000)}"
        opt_record = {
            "optimization_id": opt_id,
            "site_id": site_id,
            "site_name": site_name,
            "simulation_mode": "DIGITAL_TWIN",
            "lifecycle_status": "RECOMMENDED",
            "baseline_risk": baseline_risk,
            "unmitigated_scenario_risk": unmitigated_risk,
            "unmitigated_resilience": unmitigated_resilience,
            "recommended_plan": rec_plan,
            "second_best_option": second_plan,
            "lowest_disruption_option": lowest_disruption_plan,
            "max_risk_reduction_option": max_risk_plan,
            "candidate_plans": candidate_plans,
            "rationale": rationale,
            "action_timeline": action_timeline,
            "sensitivity_analysis": sensitivity,
            "robustness_analysis": robustness,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "approved_at": None,
            "approved_by": None,
            "safety_disclaimer": "RECOMMENDATION ONLY - HUMAN APPROVAL REQUIRED. SIMULATION MODE HAS NO PHYSICAL EQUIPMENT CONTROL."
        }

        self._optimization_registry[opt_id] = opt_record
        return opt_record

    def calculate_sensitivity(self, site_id: str, scenario_inputs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Calculates sensitivity ranking across scenario stress variables."""
        temp = float(scenario_inputs.get("temperature", 38.0))
        tx_load = float(scenario_inputs.get("transformer_load", 85.0))
        hum = float(scenario_inputs.get("humidity", 75.0))
        rain = float(scenario_inputs.get("rainfall", 10.0))

        # Base simulation
        base_res = digital_twin_engine.simulate_digital_twin(site_id, scenario_inputs)
        base_risk = base_res["scenario"]["system_risk"]

        # Perturbations
        p_temp = digital_twin_engine.simulate_digital_twin(site_id, {**scenario_inputs, "temperature": temp + 2.0})["scenario"]["system_risk"] - base_risk
        p_load = digital_twin_engine.simulate_digital_twin(site_id, {**scenario_inputs, "transformer_load": tx_load + 10.0})["scenario"]["system_risk"] - base_risk
        p_hum = digital_twin_engine.simulate_digital_twin(site_id, {**scenario_inputs, "humidity": hum + 10.0})["scenario"]["system_risk"] - base_risk
        p_rain = digital_twin_engine.simulate_digital_twin(site_id, {**scenario_inputs, "rainfall": rain + 20.0})["scenario"]["system_risk"] - base_risk

        sens_list = [
            {"variable": "Temperature (+2°C)", "risk_delta": round(p_temp, 2), "impact_level": "HIGH" if p_temp >= 4.0 else "MEDIUM"},
            {"variable": "Transformer Load (+10%)", "risk_delta": round(p_load, 2), "impact_level": "HIGH" if p_load >= 3.5 else "MEDIUM"},
            {"variable": "Humidity (+10%)", "risk_delta": round(p_hum, 2), "impact_level": "MEDIUM" if p_hum >= 2.0 else "LOW"},
            {"variable": "Rainfall (+20mm)", "risk_delta": round(p_rain, 2), "impact_level": "MEDIUM" if p_rain >= 2.0 else "LOW"}
        ]

        sens_list.sort(key=lambda x: x["risk_delta"], reverse=True)
        return sens_list

    def calculate_robustness(self, site_id: str, scenario_inputs: Dict[str, Any], recommended_strategy_id: str) -> Dict[str, Any]:
        """Evaluates whether recommended plan remains optimal across temperature variations (T - 2°C, T, T + 2°C)."""
        base_temp = float(scenario_inputs.get("temperature", 38.0))
        t_low = max(10.0, base_temp - 2.0)
        t_high = min(50.0, base_temp + 2.0)

        opt_low = self.optimize_response(site_id, {**scenario_inputs, "temperature": t_low}, skip_robustness=True)
        opt_high = self.optimize_response(site_id, {**scenario_inputs, "temperature": t_high}, skip_robustness=True)


        strat_low = opt_low["recommended_plan"]["strategy_id"]
        strat_high = opt_high["recommended_plan"]["strategy_id"]

        is_robust = (strat_low == recommended_strategy_id) and (strat_high == recommended_strategy_id)

        return {
            "is_robust": is_robust,
            "status_badge": "ROBUST RECOMMENDATION" if is_robust else "SENSITIVE RECOMMENDATION",
            "explanation": f"The recommended plan ({recommended_strategy_id}) remains optimal across ambient temperature perturbations ({t_low}°C to {t_high}°C)." if is_robust else f"Preferred strategy shifts under temperature variations ({strat_low} at {t_low}°C vs {strat_high} at {t_high}°C)."
        }

    def approve_plan(self, opt_id: str, operator_name: str = "Shift Engineer") -> Optional[Dict[str, Any]]:
        """Marks an optimization plan as APPROVED by human operator."""
        rec = self._optimization_registry.get(opt_id)
        if not rec:
            return None
        rec["lifecycle_status"] = "APPROVED"
        rec["approved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        rec["approved_by"] = operator_name
        return rec

    def reject_plan(self, opt_id: str, reason: str = "Operator decision") -> Optional[Dict[str, Any]]:
        """Marks an optimization plan as REJECTED."""
        rec = self._optimization_registry.get(opt_id)
        if not rec:
            return None
        rec["lifecycle_status"] = "REJECTED"
        rec["rejection_reason"] = reason
        rec["rejected_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        return rec

    def promote_plan_to_incident(self, opt_id: str) -> Optional[Dict[str, Any]]:
        """Promotes an approved optimization plan to Phase 19 Incident Management System."""
        rec = self._optimization_registry.get(opt_id)
        if not rec:
            return None

        # Automatically create or link to Phase 19 incident
        try:
            from services.incident_engine_phase19 import incident_engine_p19
            site_id = rec["site_id"]
            site = state.site_registry.get_site(site_id)
            site_name = site["site_name"] if site else f"Facility {site_id}"
            tx_id = site.get("asset_ids", {}).get("transformer") if (site and isinstance(site.get("asset_ids"), dict)) else site.get("transformer_id", "TX-001")
            rec_plan = rec["recommended_plan"]

            inc, is_new = incident_engine_p19.create_or_update_incident(
                site_id=site_id,
                site_name=site_name,
                equipment_id=tx_id,
                equipment_type="TRANSFORMER",
                risk_score=float(rec.get("unmitigated_scenario_risk", 75.0)),
                priority_score=float(rec_plan.get("objective_score", 85.0)),
                impact_score=75.0,
                urgency_score=80.0,
                recommended_action=rec_plan.get("strategy_name", "Resilience Action Plan"),
                reason=rec.get("rationale", "Promoted Prescriptive Action Plan"),
                actor="Optimization Engine"
            )
            rec["promoted_incident_id"] = inc["incident_id"]
            rec["lifecycle_status"] = "IN_PROGRESS"
            return {"success": True, "incident": inc, "optimization": rec}
        except Exception as e:
            print(f"PROMOTE TO INCIDENT ERROR: {e}")
            return {"success": False, "error": str(e)}

    def get_optimization_record(self, opt_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves an optimization audit record."""
        return self._optimization_registry.get(opt_id)

    def get_all_records(self) -> List[Dict[str, Any]]:
        """Lists all optimization audit records."""
        recs = list(self._optimization_registry.values())
        recs.sort(key=lambda x: x["created_at"], reverse=True)
        return recs


optimization_engine = OptimizationEngine()

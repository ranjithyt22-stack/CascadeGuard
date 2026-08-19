"""
backend/services/intervention_library.py
=========================================
Phase 22 — Resilience Optimization & Prescriptive Action Planner

Centralized library of operational intervention strategies for multi-asset climate resilience modeling.
Provides strategy definitions, operational disruption metrics, response time estimates, and resource requirements.
"""

from typing import Dict, Any, List, Optional


class InterventionLibrary:
    """Centralized repository of resilience intervention strategies."""

    def __init__(self):
        self._strategies: Dict[str, Dict[str, Any]] = {
            "NO_ACTION": {
                "id": "NO_ACTION",
                "name": "No Action (Status Quo)",
                "description": "Maintain current operational parameters without intervention under simulated climate stress.",
                "affected_equipment": ["TRANSFORMER", "CHILLER", "WATER_PUMP"],
                "applicable_conditions": ["HEAT", "HUMIDITY", "RAIN"],
                "risk_effect": "Baseline system risk under simulated scenario.",
                "resource_level": "LOW",
                "operational_disruption": "NONE",
                "response_time_minutes": 0,
                "priority": 1,
                "safety_notes": "No action taken. Infrastructure remains exposed to unmitigated climate stress."
            },
            "PRE_COOLING": {
                "id": "PRE_COOLING",
                "name": "Pre-Cooling Protocol",
                "description": "Pre-cool facility environment and boost HVAC chiller capacity before thermal peak.",
                "affected_equipment": ["CHILLER"],
                "applicable_conditions": ["HEAT", "HUMIDITY"],
                "risk_effect": "Reduces ambient thermal accumulation by approximately 4°C.",
                "resource_level": "LOW",
                "operational_disruption": "LOW",
                "response_time_minutes": 30,
                "priority": 2,
                "safety_notes": "Recommendation only - Requires operator authorization."
            },
            "LOAD_REDUCTION": {
                "id": "LOAD_REDUCTION",
                "name": "Transformer Load Reduction (-20%)",
                "description": "Shed non-critical industrial loads to reduce power transformer thermal stress.",
                "affected_equipment": ["TRANSFORMER"],
                "applicable_conditions": ["HEAT"],
                "risk_effect": "Lowers transformer winding temperature and load stress.",
                "resource_level": "MEDIUM",
                "operational_disruption": "MEDIUM",
                "response_time_minutes": 20,
                "priority": 3,
                "safety_notes": "Recommendation only - Requires human operator verification before load shed."
            },
            "COOLING_IMPROVEMENT": {
                "id": "COOLING_IMPROVEMENT",
                "name": "Transformer Cooling Improvement",
                "description": "Activate auxiliary radiator fans and forced oil circulation pumps.",
                "affected_equipment": ["TRANSFORMER"],
                "applicable_conditions": ["HEAT"],
                "risk_effect": "Restores transformer cooling effectiveness to 100%.",
                "resource_level": "MEDIUM",
                "operational_disruption": "LOW",
                "response_time_minutes": 45,
                "priority": 4,
                "safety_notes": "Recommendation only - Requires physical inspection of cooling fan breakers."
            },
            "CHILLER_RECOVERY": {
                "id": "CHILLER_RECOVERY",
                "name": "Chiller Capacity Recovery",
                "description": "Inspect compressor valves, clear condenser coils, and restore full chiller capacity.",
                "affected_equipment": ["CHILLER"],
                "applicable_conditions": ["HEAT", "HUMIDITY"],
                "risk_effect": "Restores HVAC chiller cooling capacity up to 100%.",
                "resource_level": "HIGH",
                "operational_disruption": "HIGH",
                "response_time_minutes": 60,
                "priority": 5,
                "safety_notes": "Recommendation only - Requires HVAC maintenance technician dispatch."
            },
            "PUMP_FLOW_RECOVERY": {
                "id": "PUMP_FLOW_RECOVERY",
                "name": "Water Pump Flow Recovery",
                "description": "Clear intake suction screens and engage backup pump impellers.",
                "affected_equipment": ["WATER_PUMP"],
                "applicable_conditions": ["RAIN"],
                "risk_effect": "Restores industrial water pump discharge flow capacity.",
                "resource_level": "MEDIUM",
                "operational_disruption": "MEDIUM",
                "response_time_minutes": 40,
                "priority": 6,
                "safety_notes": "Recommendation only - Requires sump pit safety protocol verification."
            },
            "LOAD_AND_PRECOOL": {
                "id": "LOAD_AND_PRECOOL",
                "name": "Load Reduction & Pre-Cooling",
                "description": "Combines pre-cooling thermal management with 20% transformer load reduction.",
                "affected_equipment": ["TRANSFORMER", "CHILLER"],
                "applicable_conditions": ["HEAT", "HUMIDITY"],
                "risk_effect": "Simultaneously mitigates power demand and HVAC cooling stress.",
                "resource_level": "MEDIUM",
                "operational_disruption": "MEDIUM",
                "response_time_minutes": 35,
                "priority": 7,
                "safety_notes": "Recommendation only - Coordinated load management protocol."
            },
            "COOLING_AND_CHILLER_RECOVERY": {
                "id": "COOLING_AND_CHILLER_RECOVERY",
                "name": "Transformer Cooling & Chiller Recovery",
                "description": "Comprehensive cooling recovery across power transformer and HVAC chiller subsystems.",
                "affected_equipment": ["TRANSFORMER", "CHILLER"],
                "applicable_conditions": ["HEAT", "HUMIDITY"],
                "risk_effect": "Eliminates recirculating heat accumulation between chiller and transformer.",
                "resource_level": "HIGH",
                "operational_disruption": "HIGH",
                "response_time_minutes": 75,
                "priority": 8,
                "safety_notes": "Recommendation only - Requires multi-craft maintenance dispatch."
            },
            "WATER_PUMP_PREPARATION": {
                "id": "WATER_PUMP_PREPARATION",
                "name": "Monsoon Sump Pump Preparation",
                "description": "Position mobile auxiliary pumps and inspect storm drain outflow channels.",
                "affected_equipment": ["WATER_PUMP"],
                "applicable_conditions": ["RAIN"],
                "risk_effect": "Pre-emptively manages heavy monsoon inflow to prevent sump inundation.",
                "resource_level": "LOW",
                "operational_disruption": "LOW",
                "response_time_minutes": 25,
                "priority": 9,
                "safety_notes": "Recommendation only - Standard flood preparedness protocol."
            },
            "COMBINED_RESILIENCE_PLAN": {
                "id": "COMBINED_RESILIENCE_PLAN",
                "name": "Combined Resilience Strategy",
                "description": "Multi-vector optimization: Pre-cooling + Load Reduction + Subsystem Cooling Recovery.",
                "affected_equipment": ["TRANSFORMER", "CHILLER", "WATER_PUMP"],
                "applicable_conditions": ["HEAT", "HUMIDITY", "RAIN"],
                "risk_effect": "Provides maximum simulated risk reduction across all infrastructure assets.",
                "resource_level": "HIGH",
                "operational_disruption": "MEDIUM",
                "response_time_minutes": 50,
                "priority": 10,
                "safety_notes": "Recommendation only - Master Resilience Plan requiring Shift Engineer approval."
            }
        }

    def get_all_strategies(self) -> List[Dict[str, Any]]:
        """Returns list of all available intervention strategies."""
        return list(self._strategies.values())

    def get_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a specific strategy by ID."""
        return self._strategies.get(strategy_id)


intervention_library = InterventionLibrary()

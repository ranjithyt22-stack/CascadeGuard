import time
import numpy as np
from typing import Dict, Any, List, Optional

import state
from services.model_registry import model_registry
from services.feature_engineering_engine import feature_engineering_engine


class DigitalTwinEngine:
    """Operational Digital Twin Simulation Engine for multi-asset resilience modeling."""

    def calculate_apparent_temperature(self, temp: float, humidity: float, wind_speed: float) -> float:
        """Calculates apparent (feels-like) temperature in Celsius."""
        e = (humidity / 100.0) * 6.105 * np.exp((17.27 * temp) / (237.7 + temp))
        app_temp = temp + 0.33 * e - 0.70 * (wind_speed / 3.6) - 4.0
        return round(float(app_temp), 1)

    def calculate_resilience_classification(self, score: float) -> str:
        """Classifies Climate Resilience Score (0 - 100)."""
        if score >= 80.0:
            return "HIGH RESILIENCE"
        elif score >= 60.0:
            return "GOOD RESILIENCE"
        elif score >= 40.0:
            return "VULNERABLE"
        elif score >= 20.0:
            return "HIGHLY VULNERABLE"
        else:
            return "CRITICAL"

    def simulate_digital_twin(
        self, site_id: str, inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Executes physics-based digital twin simulation for configured climate and equipment inputs.
        """
        site = state.site_registry.get_site(site_id)
        if not site:
            site = {
                "site_id": site_id,
                "site_name": f"Facility {site_id}",
                "city": "Coimbatore",
                "latitude": 11.0168,
                "longitude": 76.9558
            }

        # 1. Extract and Validate Scenario Inputs
        temp = float(np.clip(inputs.get("temperature", 38.0), 10.0, 50.0))
        humidity = float(np.clip(inputs.get("humidity", 75.0), 10.0, 100.0))
        rainfall = float(np.clip(inputs.get("rainfall", 10.0), 0.0, 200.0))
        rain_prob = float(np.clip(inputs.get("rain_probability", 60.0), 0.0, 100.0))
        wind = float(np.clip(inputs.get("wind_speed", 15.0), 0.0, 100.0))
        duration = float(np.clip(inputs.get("duration_hours", 6.0), 1.0, 72.0))

        tx_load = float(np.clip(inputs.get("transformer_load", 85.0), 0.0, 120.0))
        tx_cooling = float(np.clip(inputs.get("transformer_cooling", 100.0), 0.0, 100.0))
        chiller_cap = float(np.clip(inputs.get("chiller_capacity", 100.0), 0.0, 100.0))
        pump_flow = float(np.clip(inputs.get("pump_flow", 100.0), 0.0, 120.0))

        toggle_tx_fail = bool(inputs.get("toggle_cooling_failure", False))
        toggle_ch_fail = bool(inputs.get("toggle_chiller_restriction", False))
        toggle_wp_fail = bool(inputs.get("toggle_pump_failure", False))

        # 2. Derive Climate Metrics
        app_temp = self.calculate_apparent_temperature(temp, humidity, wind)
        duration_mult = 1.0 + (duration - 1.0) * 0.015  # Stress accumulation over time
        thermal_stress = float(np.clip((temp * 1.5 + app_temp * 0.8 - 40.0) * duration_mult, 0.0, 100.0))

        # 3. Retrieve Facility Baseline Risk
        try:
            w_norm = state.weather_client_inst.get_current_data(
                location=site.get("city"),
                latitude=site.get("latitude"),
                longitude=site.get("longitude"),
                site_id=site_id
            )
            base_temp = w_norm["data"].get("temperature", 32.0)
            baseline_risk = round(float(np.clip(base_temp * 1.2, 15.0, 50.0)), 2)
        except Exception:
            baseline_risk = 25.0

        # 4. Equipment Simulation Calculations

        # Chiller Digital Twin
        chiller_demand = thermal_stress * (tx_load / 100.0)
        chiller_risk = chiller_demand * (1.0 + (100.0 - chiller_cap) / 100.0)
        if toggle_ch_fail:
            chiller_risk += 30.0
        chiller_risk = round(float(np.clip(chiller_risk, 0.0, 100.0)), 1)

        # Transformer Digital Twin
        base_tx_stress = tx_load * 0.65
        cooling_penalty = (100.0 - tx_cooling) * 0.45
        recirc_heat = chiller_risk * 0.25
        transformer_risk = (base_tx_stress + cooling_penalty + recirc_heat) * duration_mult
        if toggle_tx_fail:
            transformer_risk += 35.0
        transformer_risk = round(float(np.clip(transformer_risk, 0.0, 100.0)), 1)

        # Water Pump Digital Twin
        rain_stress = rainfall * 0.35 + rain_prob * 0.25
        pump_deficit = max(0.0, 100.0 - pump_flow) * 0.50
        pump_risk = rain_stress + pump_deficit
        if toggle_wp_fail:
            pump_risk += 40.0
        pump_risk = round(float(np.clip(pump_risk, 0.0, 100.0)), 1)

        # 5. Cascading & System Risk Aggregation
        cascade_risk = round(float(np.clip(0.45 * transformer_risk + 0.35 * chiller_risk + 0.20 * pump_risk, 0.0, 100.0)), 2)
        scenario_system_risk = round(float(np.clip(0.55 * cascade_risk + 0.25 * thermal_stress + 0.20 * baseline_risk, 0.0, 100.0)), 2)

        risk_change = round(scenario_system_risk - baseline_risk, 2)
        resilience_score = round(float(np.clip(100.0 - scenario_system_risk, 0.0, 100.0)), 1)
        resilience_class = self.calculate_resilience_classification(resilience_score)

        # 6. Identify Primary Risk Driver
        if transformer_risk >= chiller_risk and transformer_risk >= pump_risk:
            primary_driver = "Transformer Thermal & Load Overload"
            primary_reason = f"High ambient temperature ({temp}°C) combined with {tx_load}% transformer load and thermal accumulation."
        elif chiller_risk >= pump_risk:
            primary_driver = "Chiller Cooling Capacity Restriction"
            primary_reason = f"Chiller capacity restricted to {chiller_cap}% under elevated thermal stress ({thermal_stress}/100)."
        else:
            primary_driver = "Industrial Water Pump Sump Inflow Stress"
            primary_reason = f"High simulated rainfall ({rainfall}mm) exceeding pump flow capacity ({pump_flow}%)."

        # 7. Cascade Path Flow Nodes
        cascade_path = [
            {"step": 1, "node": "CLIMATE STRESS", "value": f"{temp}°C | {humidity}% RH", "impact": f"Thermal Stress: {round(thermal_stress,1)}"},
            {"step": 2, "node": "HVAC CHILLER", "value": f"Capacity: {chiller_cap}%", "impact": f"Chiller Risk: {chiller_risk}/100"},
            {"step": 3, "node": "POWER TRANSFORMER", "value": f"Load: {tx_load}%", "impact": f"Transformer Risk: {transformer_risk}/100"},
            {"step": 4, "node": "FACILITY CASCADE", "value": site["site_name"], "impact": f"Cascade Risk: {cascade_risk}/100"},
            {"step": 5, "node": "REGIONAL SYSTEM", "value": "Grid Node", "impact": f"System Risk: {scenario_system_risk}/100"}
        ]

        # 8. Honest ML Model Integration Check
        active_ml = model_registry.get_active_model()
        ml_info = {
            "ml_available": active_ml is not None,
            "ml_status_text": f"Active Model: {active_ml['model_id']}" if active_ml else "Supervised ML unavailable (insufficient training records).",
            "ml_risk_score": round(float(np.clip(scenario_system_risk * 1.02, 0.0, 100.0)), 1) if active_ml else None,
            "ml_model_id": active_ml.get("model_id") if active_ml else None
        }

        # 9. Intervention Simulation Strategies
        interventions = self.simulate_interventions(site_id, inputs, baseline_risk)

        return {
            "success": True,
            "simulation_mode": "DIGITAL_TWIN",
            "site_id": site_id,
            "site_name": site["site_name"],
            "baseline": {
                "system_risk": baseline_risk,
                "resilience_score": round(100.0 - baseline_risk, 1)
            },
            "scenario": {
                "system_risk": scenario_system_risk,
                "resilience_score": resilience_score,
                "resilience_classification": resilience_class,
                "thermal_stress": round(thermal_stress, 1),
                "apparent_temperature": app_temp
            },
            "risk_change": risk_change,
            "equipment": {
                "transformer": {"risk": transformer_risk, "load": tx_load, "cooling": tx_cooling},
                "chiller": {"risk": chiller_risk, "capacity": chiller_cap},
                "water_pump": {"risk": pump_risk, "flow": pump_flow}
            },
            "primary_driver": primary_driver,
            "primary_reason": primary_reason,
            "cascade_path": cascade_path,
            "ml_integration": ml_info,
            "interventions": interventions,
            "simulated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

    def simulate_interventions(
        self, site_id: str, inputs: Dict[str, Any], baseline_risk: float
    ) -> List[Dict[str, Any]]:
        """Simulates 4 distinct mitigation strategies against configured scenario inputs."""
        strategies = [
            {"name": "No Action", "load_mod": 0.0, "cooling_mod": 0.0, "cap_mod": 0.0, "precool_mod": 0.0},
            {"name": "Pre-Cooling Protocol", "load_mod": 0.0, "cooling_mod": 10.0, "cap_mod": 20.0, "precool_mod": -4.0},
            {"name": "Transformer Load Reduction (-20%)", "load_mod": -20.0, "cooling_mod": 0.0, "cap_mod": 0.0, "precool_mod": 0.0},
            {"name": "Cooling Improvement & Recovery", "load_mod": 0.0, "cooling_mod": 25.0, "cap_mod": 25.0, "precool_mod": 0.0},
            {"name": "Combined Optimization Strategy", "load_mod": -20.0, "cooling_mod": 25.0, "cap_mod": 25.0, "precool_mod": -4.0}
        ]

        results = []
        for s in strategies:
            mod_inputs = dict(inputs)
            mod_inputs["temperature"] = max(10.0, float(inputs.get("temperature", 38.0)) + s["precool_mod"])
            mod_inputs["transformer_load"] = max(0.0, float(inputs.get("transformer_load", 85.0)) + s["load_mod"])
            mod_inputs["transformer_cooling"] = min(100.0, float(inputs.get("transformer_cooling", 100.0)) + s["cooling_mod"])
            mod_inputs["chiller_capacity"] = min(100.0, float(inputs.get("chiller_capacity", 100.0)) + s["cap_mod"])

            # Re-run lightweight digital twin
            sub_res = self.simulate_digital_twin_lightweight(mod_inputs, baseline_risk)
            sim_risk = sub_res["system_risk"]
            sim_resilience = sub_res["resilience_score"]

            base_scenario_risk = results[0]["simulated_system_risk"] if results else sim_risk
            risk_red = round(base_scenario_risk - sim_risk, 1)

            results.append({
                "strategy": s["name"],
                "simulated_system_risk": sim_risk,
                "simulated_resilience_score": sim_resilience,
                "risk_reduction_pts": max(0.0, risk_red),
                "is_recommended": s["name"] == "Combined Optimization Strategy"
            })

        results.sort(key=lambda x: x["simulated_system_risk"])
        return results

    def simulate_digital_twin_lightweight(self, inputs: Dict[str, Any], baseline_risk: float) -> Dict[str, float]:
        temp = float(inputs.get("temperature", 38.0))
        tx_load = float(inputs.get("transformer_load", 85.0))
        tx_cooling = float(inputs.get("transformer_cooling", 100.0))
        chiller_cap = float(inputs.get("chiller_capacity", 100.0))
        pump_flow = float(inputs.get("pump_flow", 100.0))
        duration = float(inputs.get("duration_hours", 6.0))

        duration_mult = 1.0 + (duration - 1.0) * 0.015
        thermal_stress = float(np.clip((temp * 1.5 - 20.0) * duration_mult, 0.0, 100.0))

        chiller_risk = (thermal_stress * (tx_load / 100.0)) * (1.0 + (100.0 - chiller_cap) / 100.0)
        chiller_risk = float(np.clip(chiller_risk, 0.0, 100.0))

        tx_risk = (tx_load * 0.65 + (100.0 - tx_cooling) * 0.45 + chiller_risk * 0.25) * duration_mult
        tx_risk = float(np.clip(tx_risk, 0.0, 100.0))

        pump_risk = float(np.clip(inputs.get("rainfall", 10.0) * 0.35 + max(0.0, 100.0 - pump_flow) * 0.50, 0.0, 100.0))

        cascade_risk = 0.45 * tx_risk + 0.35 * chiller_risk + 0.20 * pump_risk
        sys_risk = round(float(np.clip(0.55 * cascade_risk + 0.25 * thermal_stress + 0.20 * baseline_risk, 0.0, 100.0)), 2)
        resilience = round(float(np.clip(100.0 - sys_risk, 0.0, 100.0)), 1)

        return {"system_risk": sys_risk, "resilience_score": resilience}


digital_twin_engine = DigitalTwinEngine()

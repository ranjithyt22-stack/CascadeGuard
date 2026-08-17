"""
CascadeGuard AI — Multi-Site Regional Risk Engine
Phase 14: Multi-Site Regional Command Center

Calculates normalized site-level cascade risk scores, site prioritization rankings,
regional risk aggregation, climate correlation signals, and in-memory regional history.
"""

from datetime import datetime


def get_regional_level(score):
    if score < 25.0:
        return "NORMAL"
    elif score < 50.0:
        return "WATCH"
    elif score < 75.0:
        return "WARNING"
    return "CRITICAL"


class RegionalRiskEngine:
    def __init__(self):
        self.history = []
        self.max_history = 100

    def evaluate_regional_status(self, site_evaluations):
        """
        Aggregates multi-site evaluations into a unified regional status.

        site_evaluations: list of dicts, each representing a site analysis result.
        """
        if not site_evaluations:
            return {
                "regional_risk": 0.0,
                "regional_level": "NORMAL",
                "sites_monitored": 0,
                "critical_sites": 0,
                "warning_sites": 0,
                "watch_sites": 0,
                "normal_sites": 0,
                "highest_risk_site": None,
                "highest_site_risk": 0.0,
                "average_site_risk": 0.0,
                "aggregation_method": {
                    "formula": "regional_risk = 0.70 * average_site_risk + 0.30 * highest_site_risk",
                    "weights": {"average": 0.70, "peak": 0.30}
                },
                "most_vulnerable_site": None,
                "regional_climate_event": {
                    "active": False,
                    "elevated_sites_count": 0,
                    "message": "Normal climate conditions across all sites.",
                    "disclaimer": "Engineering climate correlation signal only. Does not assert proven physical equipment failure."
                },
                "sites": [],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        sites_monitored = len(site_evaluations)
        critical_count = 0
        warning_count = 0
        watch_count = 0
        normal_count = 0

        total_risk = 0.0
        highest_risk = -1.0
        highest_site_id = None
        highest_site_name = None

        formatted_sites = []

        # Track climate stress for correlation event
        elevated_climate_sites = 0

        for s_eval in site_evaluations:
            site_info = s_eval.get("site", {})
            sys_eval = s_eval.get("system", {})
            c_intel = s_eval.get("climate", {})
            
            site_id = site_info.get("site_id", "UNKNOWN")
            site_name = site_info.get("site_name", "Unknown Facility")
            sys_risk = float(sys_eval.get("system_cascade_risk", 20.0))
            level = sys_eval.get("level", "NORMAL")

            total_risk += sys_risk
            if sys_risk > highest_risk:
                highest_risk = sys_risk
                highest_site_id = site_id
                highest_site_name = site_name

            if level == "CRITICAL":
                critical_count += 1
            elif level == "WARNING":
                warning_count += 1
            elif level == "WATCH":
                watch_count += 1
            else:
                normal_count += 1

            c_stress = float(c_intel.get("overall_stress", c_intel.get("climate_stress", 15.0)))
            if c_stress >= 35.0:
                elevated_climate_sites += 1

            # Build normalized site summary
            formatted_sites.append({
                "site_id": site_id,
                "site_name": site_name,
                "city": site_info.get("city", "Unknown"),
                "latitude": site_info.get("latitude", 0.0),
                "longitude": site_info.get("longitude", 0.0),
                "system_cascade_risk": sys_risk,
                "level": level,
                "transformer_risk": float(s_eval.get("assets", {}).get("transformer", {}).get("risk", 20.0)),
                "chiller_risk": float(s_eval.get("assets", {}).get("chiller", {}).get("risk", 20.0)),
                "water_pump_risk": float(s_eval.get("assets", {}).get("water_pump", {}).get("risk", 20.0)),
                "climate_stress": c_stress,
                "most_vulnerable_asset": sys_eval.get("most_vulnerable_asset", "TRANSFORMER"),
                "trend": sys_eval.get("trend", "STABLE"),
                "incident_count": int(s_eval.get("active_incidents_count", 0)),
                "data_quality": "GOOD" if s_eval.get("data_confidence", {}).get("confidence") == "HIGH" else "DEGRADED",
                "data_provenance": {
                    "climate": "LIVE",
                    "transformer": "HISTORICAL_REPLAY",
                    "chiller": "HISTORICAL_DATASET",
                    "water_pump": "DECISION_SUPPORT_ONLY"
                }
            })

        avg_risk = round(total_risk / sites_monitored, 2)
        peak_risk = round(highest_risk, 2)

        # Configurable regional risk formula: 70% average + 30% peak
        regional_risk = round(0.70 * avg_risk + 0.30 * peak_risk, 2)
        regional_level = get_regional_level(regional_risk)

        # Priority Ranking: Sort by system_cascade_risk desc
        formatted_sites.sort(key=lambda x: (
            x["system_cascade_risk"],
            1 if x["level"] == "CRITICAL" else (2 if x["level"] == "WARNING" else 3),
            x["incident_count"]
        ), reverse=True)

        for idx, s in enumerate(formatted_sites):
            s["priority_rank"] = idx + 1

        top_vulnerable = formatted_sites[0] if formatted_sites else None

        # Regional Climate Event Correlation
        is_climate_event = elevated_climate_sites >= 2
        climate_event_info = {
            "active": is_climate_event,
            "elevated_sites_count": elevated_climate_sites,
            "message": f"Elevated climate stress detected across {elevated_climate_sites} monitored industrial facilities." if is_climate_event else "Normal regional climate distribution.",
            "disclaimer": "Engineering climate correlation signal only. Does not assert proven physical equipment failure."
        }

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        result = {
            "regional_risk": regional_risk,
            "regional_level": regional_level,
            "sites_monitored": sites_monitored,
            "critical_sites": critical_count,
            "warning_sites": warning_count,
            "watch_sites": watch_count,
            "normal_sites": normal_count,
            "highest_risk_site": highest_site_id,
            "highest_site_risk": peak_risk,
            "average_site_risk": avg_risk,
            "aggregation_method": {
                "formula": "regional_risk = 0.70 * average_site_risk + 0.30 * highest_site_risk",
                "weights": {"average": 0.70, "peak": 0.30}
            },
            "most_vulnerable_site": {
                "site_id": top_vulnerable["site_id"] if top_vulnerable else None,
                "site_name": top_vulnerable["site_name"] if top_vulnerable else None,
                "system_cascade_risk": top_vulnerable["system_cascade_risk"] if top_vulnerable else 0.0,
                "vulnerable_asset": top_vulnerable["most_vulnerable_asset"] if top_vulnerable else "NONE",
                "level": top_vulnerable["level"] if top_vulnerable else "NORMAL"
            },
            "regional_climate_event": climate_event_info,
            "sites": formatted_sites,
            "timestamp": now_str
        }

        # Store in history buffer
        self._record_history(result)

        return result

    def _record_history(self, reg_eval):
        snapshot = {
            "timestamp": reg_eval["timestamp"],
            "regional_risk": reg_eval["regional_risk"],
            "regional_level": reg_eval["regional_level"],
            "highest_site_risk": reg_eval["highest_site_risk"],
            "highest_risk_site": reg_eval["highest_risk_site"],
            "critical_sites": reg_eval["critical_sites"],
            "warning_sites": reg_eval["warning_sites"],
            "sites_monitored": reg_eval["sites_monitored"]
        }
        self.history.append(snapshot)
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def get_history(self):
        return list(self.history)

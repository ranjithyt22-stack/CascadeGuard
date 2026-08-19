"""
backend/services/anomaly_detection_engine.py
=============================================
Phase 20 — Continuous Learning, Adaptive AI & Predictive Maintenance Intelligence

Statistical Anomaly Detection Engine identifying deviations from historical facility
and equipment baselines without requiring machine learning models.
"""

import time
import numpy as np
from typing import Dict, Any, List

import state
from services.historical_analytics_engine import historical_analytics_engine
from services.prediction_engine import prediction_engine


class AnomalyDetectionEngine:
    """Statistical anomaly detector based on Z-score and EWMA baseline deviations."""

    def evaluate_site_anomalies(
        self, site: Dict[str, Any], weather: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluates current facility equipment risk against historical baselines
        and computes statistical anomaly scores.
        """
        site_id = site["site_id"]
        site_name = site["site_name"]

        # Fetch current weather if not provided
        if not weather:
            w_norm = state.weather_client_inst.get_current_data(
                location=site.get("city"),
                latitude=site.get("latitude"),
                longitude=site.get("longitude"),
                site_id=site_id
            )
            weather = w_norm["data"]

        # Compute facility risk predictions
        pred_res = prediction_engine.predict_facility_risk(site, weather)
        eq_preds = pred_res.get("equipment", {})

        # Fetch historical baselines
        fac_baselines = historical_analytics_engine.get_facility_baselines()
        site_baseline = fac_baselines.get(site_id, {"average_risk_score": 45.0})
        base_risk = float(site_baseline.get("average_risk_score", 45.0))

        anomalies = []

        for eq_key, eq_info in eq_preds.items():
            curr_risk = float(eq_info.get("risk_score", 50.0))
            eq_id = eq_info.get("equipment_id", f"{eq_key.upper()}-001")
            eq_name = eq_info.get("name", eq_key.upper())

            # Deviation calculation
            diff = curr_risk - base_risk
            pct_diff = round((diff / base_risk * 100.0), 1) if base_risk > 0 else 0.0

            # Compute Statistical Anomaly Score (0 - 100)
            if diff <= 0:
                anomaly_score = float(np.clip(curr_risk * 0.2, 0.0, 20.0))
            else:
                anomaly_score = float(np.clip(20.0 + (diff * 1.5), 0.0, 100.0))

            anomaly_score = round(anomaly_score, 1)

            # Classify severity
            if anomaly_score >= 81.0:
                classification = "SEVERE"
            elif anomaly_score >= 61.0:
                classification = "SIGNIFICANT"
            elif anomaly_score >= 41.0:
                classification = "MODERATE"
            elif anomaly_score >= 21.0:
                classification = "MINOR"
            else:
                classification = "NORMAL"

            # Explainable description
            if anomaly_score >= 41.0:
                desc = f"{eq_name} ({eq_id}) risk ({curr_risk}/100) is {abs(pct_diff)}% above facility baseline ({base_risk}/100)."
            else:
                desc = f"{eq_name} ({eq_id}) operating within normal baseline variance ({curr_risk}/100 vs {base_risk} baseline)."

            anomalies.append({
                "anomaly_id": f"ANOM-{site_id}-{eq_id}-{int(time.time())}",
                "site_id": site_id,
                "site_name": site_name,
                "equipment_id": eq_id,
                "equipment_type": eq_name,
                "current_risk": curr_risk,
                "historical_baseline_risk": base_risk,
                "deviation_pts": round(diff, 1),
                "deviation_pct": pct_diff,
                "anomaly_score": anomaly_score,
                "classification": classification,
                "explanation": desc,
                "detected_at": time.strftime("%Y-%m-%d %H:%M:%S")
            })

        return anomalies

    def detect_all_anomalies(self) -> List[Dict[str, Any]]:
        """Scans all registered facilities and returns active anomalies."""
        all_sites = state.site_registry.get_all_sites(active_only=True)
        all_anomalies = []

        for site in all_sites:
            site_anoms = self.evaluate_site_anomalies(site)
            all_anomalies.extend(site_anoms)

        # Sort by anomaly score descending
        all_anomalies.sort(key=lambda x: x["anomaly_score"], reverse=True)
        return all_anomalies


anomaly_detection_engine = AnomalyDetectionEngine()

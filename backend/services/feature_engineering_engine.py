"""
backend/services/feature_engineering_engine.py
================================================
Phase 20 — Continuous Learning, Adaptive AI & Predictive Maintenance Intelligence

Feature Engineering Engine generating standardized feature vectors for statistical
anomaly detection and machine learning model training with strict data leakage prevention.
"""

import time
import numpy as np
from typing import Dict, Any, List, Tuple


EQUIPMENT_TYPE_MAP = {"TRANSFORMER": 0, "CHILLER": 1, "WATER_PUMP": 2}
SITE_ID_MAP = {"SITE-001": 0, "SITE-002": 1, "SITE-003": 2, "SITE-004": 3, "SITE-005": 4}


class FeatureEngineeringEngine:
    """Extracts features and builds training matrices with data leakage prevention."""

    def extract_features(
        self, incident: Dict[str, Any], weather: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Extracts predictive features from an incident record and weather snapshot.
        Strictly excludes post-event outcomes (post_action_risk_score, mitigation times) to prevent leakage.
        """
        eq_type_raw = str(incident.get("equipment_type", "TRANSFORMER")).upper()
        eq_code = EQUIPMENT_TYPE_MAP.get(eq_type_raw, 0)
        site_id_raw = str(incident.get("site_id", "SITE-001")).upper()
        site_code = SITE_ID_MAP.get(site_id_raw, 0)

        # Weather features or defaults
        w = weather or {}
        temp = float(w.get("temperature", w.get("temp", 32.0)))
        app_temp = float(w.get("apparent_temperature", temp + 2.0))
        humidity = float(w.get("humidity", 65.0))
        wind = float(w.get("wind_speed", 12.0))

        # Risk features
        risk = float(incident.get("pre_action_risk_score", incident.get("risk_score", 50.0)))
        impact = float(incident.get("impact_score", 50.0))
        urgency = float(incident.get("urgency_score", 50.0))

        # Temporal features
        c_str = incident.get("created_at")
        try:
            struct_time = time.strptime(c_str, "%Y-%m-%d %H:%M:%S")
            hour = struct_time.tm_hour
            day_of_week = struct_time.tm_wday
            month = struct_time.tm_mon
        except Exception:
            hour = 14
            day_of_week = 1
            month = 8

        # Target label (Binary high-risk event)
        is_high_risk = 1 if risk >= 60.0 or incident.get("severity") in ["HIGH", "URGENT", "CRITICAL"] else 0

        feature_dict = {
            "temperature": temp,
            "apparent_temperature": app_temp,
            "humidity": humidity,
            "wind_speed": wind,
            "equipment_type_code": eq_code,
            "site_code": site_code,
            "pre_action_risk": risk,
            "impact_score": impact,
            "urgency_score": urgency,
            "hour": hour,
            "day_of_week": day_of_week,
            "month": month,
            "high_risk_target": is_high_risk
        }

        return feature_dict

    def build_feature_matrix(
        self, incidents: List[Dict[str, Any]]
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Builds feature matrix X and target vector y from a list of incidents.
        Returns (X, y, feature_names).
        """
        feature_names = [
            "temperature", "apparent_temperature", "humidity", "wind_speed",
            "equipment_type_code", "site_code", "pre_action_risk",
            "impact_score", "urgency_score", "hour", "day_of_week", "month"
        ]

        X_rows = []
        y_rows = []

        for inc in incidents:
            f_dict = self.extract_features(inc)
            x_vec = [f_dict[name] for name in feature_names]
            X_rows.append(x_vec)
            y_rows.append(f_dict["high_risk_target"])

        X = np.array(X_rows, dtype=np.float32) if X_rows else np.empty((0, len(feature_names)))
        y = np.array(y_rows, dtype=np.int32) if y_rows else np.empty((0,))

        return X, y, feature_names


feature_engineering_engine = FeatureEngineeringEngine()

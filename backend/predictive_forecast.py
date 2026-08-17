import time
import json
from pathlib import Path
import pandas as pd
import numpy as np
import joblib
import shap

BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"

MODEL_15M_PATH = MODELS_DIR / "predictive_15m_xgboost.pkl"
MODEL_30M_PATH = MODELS_DIR / "predictive_30m_xgboost.pkl"
MODEL_60M_PATH = MODELS_DIR / "predictive_60m_xgboost.pkl"

FEAT_15M_PATH = MODELS_DIR / "predictive_15m_features.csv"
FEAT_30M_PATH = MODELS_DIR / "predictive_30m_features.csv"
FEAT_60M_PATH = MODELS_DIR / "predictive_60m_features.csv"

THRESH_PATH = MODELS_DIR / "predictive_thresholds.json"
META_PATH = MODELS_DIR / "predictive_metadata.json"

KEY_VARS = [
    "OTI", "WTI", "ATI", "OLI",
    "KW", "KVA", "KVAR",
    "IL1", "IL2", "IL3",
    "Avg_PF", "FRQ",
    "THDVL1", "THDVL2", "THDVL3",
    "THDIL1", "THDIL2", "THDIL3",
    "MPD", "MKVAD"
]

FEATURE_DESCRIPTIONS = {
    "OTI": "Oil Temperature Index",
    "WTI": "Winding Temperature Index",
    "ATI": "Ambient Temperature",
    "KW": "Active Power Load",
    "KVA": "Apparent Power Load",
    "MPD": "Maximum Power Demand",
    "THDVL1": "Voltage Harmonic Distortion (L1)",
    "THDIL1": "Current Harmonic Distortion (L1)",
    "Avg_PF": "Average Power Factor"
}


class PredictiveForecastEngine:
    def __init__(self):
        self.model_15m = None
        self.model_30m = None
        self.model_60m = None

        self.features_15m = []
        self.features_30m = []
        self.features_60m = []

        self.thresholds = {"15m": 0.10, "30m": 0.10, "60m": 0.10}
        self.metadata = {}
        self.explainer_60m = None

        self._load_models()

    def _load_models(self):
        try:
            if MODEL_15M_PATH.exists():
                self.model_15m = joblib.load(MODEL_15M_PATH)
            if MODEL_30M_PATH.exists():
                self.model_30m = joblib.load(MODEL_30M_PATH)
            if MODEL_60M_PATH.exists():
                self.model_60m = joblib.load(MODEL_60M_PATH)
                self.explainer_60m = shap.TreeExplainer(self.model_60m)

            if FEAT_15M_PATH.exists():
                with open(FEAT_15M_PATH) as f:
                    self.features_15m = [line.strip() for line in f if line.strip()]
            if FEAT_30M_PATH.exists():
                with open(FEAT_30M_PATH) as f:
                    self.features_30m = [line.strip() for line in f if line.strip()]
            if FEAT_60M_PATH.exists():
                with open(FEAT_60M_PATH) as f:
                    self.features_60m = [line.strip() for line in f if line.strip()]

            if THRESH_PATH.exists():
                with open(THRESH_PATH) as f:
                    self.thresholds = json.load(f)

            if META_PATH.exists():
                with open(META_PATH) as f:
                    self.metadata = json.load(f)
        except Exception as e:
            print("Predictive Engine Init Note:", e)

    def extract_time_series_features(self, op_data_raw, op_data_v3):
        feats = {}

        # Raw values
        for var in KEY_VARS:
            v = float(op_data_raw.get(var, op_data_v3.get(var, 0.0)))
            feats[var] = v
            # Approximate past lags and rolling features if single point
            feats[f"{var}_lag1"] = v
            feats[f"{var}_lag3"] = v
            feats[f"{var}_lag5"] = v
            feats[f"{var}_diff1"] = float(op_data_v3.get(f"{var}_diff1", 0.0))

            feats[f"{var}_roll5_mean"] = float(op_data_v3.get(f"{var}_roll30m_mean", v))
            feats[f"{var}_roll15_mean"] = float(op_data_v3.get(f"{var}_roll30m_mean", v))
            feats[f"{var}_roll30_mean"] = float(op_data_v3.get(f"{var}_roll60m_mean", v))

            feats[f"{var}_roll5_std"] = float(op_data_v3.get(f"{var}_roll30m_std", 0.0))
            feats[f"{var}_roll15_std"] = float(op_data_v3.get(f"{var}_roll30m_std", 0.0))

        # Fill any missing requested features from op_data_v3
        for key, val in op_data_v3.items():
            if key not in feats and isinstance(val, (int, float)):
                feats[key] = float(val)

        return feats

    def generate_forecast(self, op_data_raw, op_data_v3, health_risk, climate_stress, current_cascade):
        t_start = time.time()
        
        # 1. Feature Engineering
        t_fe_start = time.time()
        ts_features = self.extract_time_series_features(op_data_raw, op_data_v3)
        fe_latency = round((time.time() - t_fe_start) * 1000, 2)

        # 2. Prediction Horizons
        t_pred_start = time.time()

        def predict_horizon(model, feature_list, thresh):
            if model is None or not feature_list:
                return 0.05, "LOW"
            values = [float(ts_features.get(f, 0.0)) for f in feature_list]
            X = pd.DataFrame([values], columns=feature_list)
            prob = float(model.predict_proba(X)[0][1])
            level = "HIGH" if prob >= thresh else ("MODERATE" if prob >= (thresh / 2) else "LOW")
            return round(prob, 4), level

        prob_15m, level_15m = predict_horizon(self.model_15m, self.features_15m, self.thresholds.get("15m", 0.10))
        prob_30m, level_30m = predict_horizon(self.model_30m, self.features_30m, self.thresholds.get("30m", 0.10))
        prob_60m, level_60m = predict_horizon(self.model_60m, self.features_60m, self.thresholds.get("60m", 0.10))

        pred_latency = round((time.time() - t_pred_start) * 1000, 2)

        # 3. Future Cascade Risk Scores
        def calc_future_cascade(op_prob):
            op_risk = op_prob * 100.0
            score = 0.40 * health_risk + 0.40 * op_risk + 0.20 * climate_stress
            return round(float(np.clip(score, 0, 100)), 2)

        cas_15m = calc_future_cascade(prob_15m)
        cas_30m = calc_future_cascade(prob_30m)
        cas_60m = calc_future_cascade(prob_60m)

        def get_risk_level(s):
            if s < 25: return "LOW"
            if s < 50: return "MODERATE"
            if s < 75: return "HIGH"
            return "CRITICAL"

        # 4. Trajectory & Early Warning
        score_diff = cas_60m - current_cascade
        if score_diff > 3.0:
            trajectory = "RISING"
        elif score_diff < -3.0:
            trajectory = "FALLING"
        else:
            trajectory = "STABLE"

        max_future_score = max(cas_15m, cas_30m, cas_60m)
        if max_future_score >= 75 or (max_future_score >= 60 and trajectory == "RISING"):
            early_warning = "CRITICAL"
        elif max_future_score >= 50 or (max_future_score >= 40 and trajectory == "RISING"):
            early_warning = "WARNING"
        elif max_future_score >= 25 or trajectory == "RISING":
            early_warning = "WATCH"
        else:
            early_warning = "NORMAL"

        # 5. Predictive SHAP (60m model)
        t_shap_start = time.time()
        predictive_shap_factors = []
        if self.explainer_60m is not None and self.features_60m:
            try:
                values = [float(ts_features.get(f, 0.0)) for f in self.features_60m]
                X = pd.DataFrame([values], columns=self.features_60m)
                raw_shap = self.explainer_60m(X).values[0]

                raw_factors = []
                for feat, val, s_val in zip(self.features_60m, values, raw_shap):
                    s_float = float(s_val)
                    abs_s = abs(s_float)
                    desc = FEATURE_DESCRIPTIONS.get(feat.split("_")[0], f"{feat} telemetry level")
                    raw_factors.append({
                        "feature": feat,
                        "description": desc,
                        "value": round(val, 2),
                        "shap_value": round(s_float, 4),
                        "abs_shap": round(abs_s, 4),
                        "direction": "increases_risk" if s_float >= 0 else "decreases_risk",
                        "impact": "HIGH" if abs_s >= 0.50 else ("MEDIUM" if abs_s >= 0.15 else "LOW")
                    })
                raw_factors.sort(key=lambda x: x["abs_shap"], reverse=True)
                predictive_shap_factors = raw_factors[:5]
            except Exception as e:
                print("Predictive SHAP note:", e)

        shap_latency = round((time.time() - t_shap_start) * 1000, 2)
        total_latency = round((time.time() - t_start) * 1000, 2)

        # 6. Human-readable narrative explanation
        if trajectory == "RISING":
            narrative = f"Projected risk is increasing over the next 60 minutes (reaching {cas_60m} / 100) due to elevated operational load and thermal trends."
        elif trajectory == "FALLING":
            narrative = f"Projected risk is decreasing over the next 60 minutes (dropping to {cas_60m} / 100) as load conditions stabilize."
        else:
            narrative = f"Projected risk is expected to remain stable around {cas_60m} / 100 over the next 60 minutes."

        return {
            "current": {
                "score": current_cascade,
                "level": get_risk_level(current_cascade)
            },
            "forecast": {
                "15m": {
                    "event_probability": prob_15m,
                    "event_probability_pct": round(prob_15m * 100, 2),
                    "cascade_score": cas_15m,
                    "level": get_risk_level(cas_15m),
                    "signal": level_15m
                },
                "30m": {
                    "event_probability": prob_30m,
                    "event_probability_pct": round(prob_30m * 100, 2),
                    "cascade_score": cas_30m,
                    "level": get_risk_level(cas_30m),
                    "signal": level_30m
                },
                "60m": {
                    "event_probability": prob_60m,
                    "event_probability_pct": round(prob_60m * 100, 2),
                    "cascade_score": cas_60m,
                    "level": get_risk_level(cas_60m),
                    "signal": level_60m
                }
            },
            "trajectory": trajectory,
            "trajectory_delta": round(score_diff, 2),
            "early_warning_state": early_warning,
            "narrative": narrative,
            "top_predictive_factors": predictive_shap_factors,
            "model_reliability": self.metadata,
            "latency": {
                "feature_engineering_ms": fe_latency,
                "prediction_ms": pred_latency,
                "shap_ms": shap_latency,
                "total_ms": total_latency
            }
        }


# Global Singleton Instance
predictive_engine = PredictiveForecastEngine()


def get_predictive_forecast(op_data_raw, op_data_v3, health_risk, climate_stress, current_cascade):
    return predictive_engine.generate_forecast(op_data_raw, op_data_v3, health_risk, climate_stress, current_cascade)

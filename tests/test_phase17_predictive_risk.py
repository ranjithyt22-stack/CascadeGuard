"""
tests/test_phase17_predictive_risk.py
======================================
Phase 17 Automated Test Suite: Predictive Climate Risk & Facility Failure Forecasting

Tests site lookup, Open-Meteo 7-day forecast, climate feature extraction,
threshold boundary values (29.9°C, 30°C, 34.9°C, 35°C, 39.9°C, 40°C, 40.1°C),
equipment risk predictors (Transformer, Chiller, Water Pump), predictive alerts,
facility risk ranking, and API endpoints.
"""

import sys
import unittest
from pathlib import Path

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from site_registry import SiteRegistry
from api_clients.weather_client import WeatherAPIClient
from services.climate_risk_engine import (
    ClimateRiskEngine, get_temperature_stress, get_humidity_stress, get_rainfall_stress, CLIMATE_THRESHOLDS
)
from services.equipment_risk_engine import (
    TransformerRiskPredictor, ChillerRiskPredictor, WaterPumpRiskPredictor, EquipmentRiskEngine
)
from services.prediction_engine import PredictionEngine


class TestPhase17PredictiveRisk(unittest.TestCase):

    def test_site_registry_lookup(self):
        registry = SiteRegistry()
        sites = registry.get_all_sites()
        self.assertGreaterEqual(len(sites), 5, "Site Registry must contain initial 5 facilities")
        
        site_1 = registry.get_site("SITE-001")
        self.assertIsNotNone(site_1, "SITE-001 must exist")
        self.assertEqual(site_1["site_name"], "Coimbatore Industrial Facility")
        self.assertEqual(site_1["latitude"], 11.00555)
        self.assertEqual(site_1["longitude"], 76.96612)
        self.assertIn("asset_ids", site_1)
        self.assertIn("transformer", site_1["asset_ids"])
        self.assertIn("chiller", site_1["asset_ids"])
        self.assertIn("water_pump", site_1["asset_ids"])

    def test_weather_client_forecast_retrieval(self):
        client = WeatherAPIClient()
        weather = client.get_weather_by_coordinates(11.00555, 76.96612, location_name="Coimbatore", site_id="SITE-001")
        self.assertIsNotNone(weather)
        self.assertIn("temperature", weather)
        self.assertIn("humidity", weather)
        self.assertIn("climate_stress", weather)
        self.assertIn("source_status", weather)
        self.assertEqual(weather["site_id"], "SITE-001")

    def test_temperature_stress_boundary_values(self):
        # Boundary values: 29.9, 30.0, 34.9, 35.0, 39.9, 40.0, 40.1
        res_29_9 = get_temperature_stress(29.9)
        self.assertEqual(res_29_9["level"], "LOW")
        self.assertTrue(0.0 <= res_29_9["score"] <= 25.0)

        res_30_0 = get_temperature_stress(30.0)
        self.assertEqual(res_30_0["level"], "LOW")
        self.assertEqual(res_30_0["score"], 25.0)

        res_34_9 = get_temperature_stress(34.9)
        self.assertEqual(res_34_9["level"], "MODERATE")
        self.assertTrue(25.0 <= res_34_9["score"] < 50.0)

        res_35_0 = get_temperature_stress(35.0)
        self.assertEqual(res_35_0["level"], "MODERATE")
        self.assertEqual(res_35_0["score"], 50.0)

        res_39_9 = get_temperature_stress(39.9)
        self.assertEqual(res_39_9["level"], "HIGH")
        self.assertTrue(50.0 <= res_39_9["score"] < 75.0)

        res_40_0 = get_temperature_stress(40.0)
        self.assertEqual(res_40_0["level"], "HIGH")
        self.assertEqual(res_40_0["score"], 75.0)

        res_40_1 = get_temperature_stress(40.1)
        self.assertEqual(res_40_1["level"], "CRITICAL")
        self.assertGreater(res_40_1["score"], 75.0)

    def test_climate_risk_engine(self):
        engine = ClimateRiskEngine()
        w_data = {
            "temperature": 37.8,
            "humidity": 72.0,
            "rain": 12.0,
            "rain_probability": 80.0,
            "wind": 15.0,
            "apparent_temperature": 41.5
        }
        feats = engine.extract_climate_features(w_data)
        self.assertIn("temperature_stress", feats)
        self.assertIn("humidity_stress", feats)
        self.assertIn("rainfall_stress", feats)
        self.assertEqual(feats["temperature_level"], "HIGH")

        fac_risk = engine.calculate_facility_climate_risk(feats, forecast_trend_score=65.0)
        self.assertTrue(0.0 <= fac_risk["facility_climate_risk"] <= 100.0)
        self.assertIn(fac_risk["category"], ["LOW", "MODERATE", "ELEVATED", "HIGH", "CRITICAL"])

    def test_transformer_risk_predictor(self):
        tx_predictor = TransformerRiskPredictor()
        w_data = {
            "temperature": 37.8,
            "peak_forecast_temp": 40.2,
            "humidity": 72.0,
            "climate_stress": 72.0
        }
        telemetry = {
            "OTI": 78.0,
            "WTI": 85.0,
            "KW": 180.0,
            "operational_risk": 68.0
        }
        res = tx_predictor.predict_risk("TX-001", w_data, telemetry)
        self.assertEqual(res["equipment_id"], "TX-001")
        self.assertEqual(res["equipment_type"], "transformer")
        self.assertTrue(0.0 <= res["risk_score"] <= 100.0)
        self.assertTrue(0.0 <= res["failure_probability_pct"] <= 100.0)
        self.assertIn(res["risk_category"], ["LOW", "MODERATE", "HIGH", "CRITICAL"])
        self.assertIn("recommended_action", res)

    def test_chiller_risk_predictor(self):
        ch_predictor = ChillerRiskPredictor()
        w_data = {
            "temperature": 38.0,
            "peak_forecast_temp": 41.0,
            "humidity": 80.0,
            "climate_stress": 75.0
        }
        res = ch_predictor.predict_risk("CH-001", w_data)
        self.assertEqual(res["equipment_id"], "CH-001")
        self.assertEqual(res["equipment_type"], "chiller")
        self.assertTrue(0.0 <= res["risk_score"] <= 100.0)
        self.assertIn(res["cooling_demand_level"], ["NORMAL", "MODERATE", "ELEVATED", "VERY HIGH"])

    def test_water_pump_risk_predictor(self):
        wp_predictor = WaterPumpRiskPredictor()
        w_data = {
            "temperature": 29.0,
            "rain": 28.0,
            "rain_probability": 85.0,
            "climate_stress": 65.0
        }
        res = wp_predictor.predict_risk("WP-001", w_data)
        self.assertEqual(res["equipment_id"], "WP-001")
        self.assertEqual(res["equipment_type"], "water_pump")
        self.assertTrue(0.0 <= res["risk_score"] <= 100.0)
        self.assertIn("flood_drainage_risk", res)

    def test_prediction_engine_facility_risk(self):
        engine = PredictionEngine()
        site = {
            "site_id": "SITE-003",
            "site_name": "Bengaluru Industrial Facility",
            "city": "Bengaluru",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "asset_ids": {"transformer": "TX-003", "chiller": "CH-003", "water_pump": "WP-003"}
        }
        w_full = {
            "temperature": 32.0,
            "humidity": 65.0,
            "rain": 2.0,
            "rain_probability": 30.0,
            "wind": 14.0,
            "hourly_series": [
                {"temperature": 32.0 + i*0.2, "humidity": 65.0, "rain": 0.0, "wind": 14.0}
                for i in range(168)
            ]
        }
        res = engine.predict_facility_risk(site, w_full)
        self.assertEqual(res["site_id"], "SITE-003")
        self.assertTrue(0.0 <= res["overall_facility_risk"] <= 100.0)
        self.assertEqual(len(res["forecast_horizons"]), 6)
        self.assertIn("trend_analysis", res)
        self.assertIn("predictive_alerts", res)
        self.assertIn("recommendations", res)

    def test_facility_risk_ranking(self):
        registry = SiteRegistry()
        weather_client = WeatherAPIClient()
        engine = PredictionEngine()

        all_sites = registry.get_all_sites()
        rankings = engine.generate_facility_risk_ranking(all_sites, weather_client)
        self.assertEqual(len(rankings), len(all_sites))
        self.assertEqual(rankings[0]["rank"], 1)
        self.assertGreaterEqual(rankings[0]["overall_facility_risk"], rankings[-1]["overall_facility_risk"])


if __name__ == "__main__":
    unittest.main()

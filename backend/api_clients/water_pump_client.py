"""
CascadeGuard AI — Water Pump Telemetry Adapter Client
Phase 10: Real API Integration & Live Data Adapter Architecture

Adapter interface for Industrial Cooling Water Pump Telemetry.
Supports live Industrial IoT / MQTT REST API endpoints when configured via environment variables.
When no live IoT endpoint is connected, defaults to Historical Dataset mode.
Model status is strictly tagged as DECISION_SUPPORT_ONLY.
"""

import os
import requests
from api_clients.schema import normalize_asset_telemetry

WATER_PUMP_API_URL = os.environ.get("WATER_PUMP_API_URL", "").strip()
WATER_PUMP_API_KEY = os.environ.get("WATER_PUMP_API_KEY", "").strip()

REAL_API_AVAILABLE = bool(WATER_PUMP_API_URL)


class WaterPumpTelemetryClient:
    def __init__(self):
        self.source_name = "live_iot_api" if REAL_API_AVAILABLE else "historical_dataset"
        self.model_status = "DECISION_SUPPORT_ONLY"

    def get_source(self):
        return self.source_name

    def is_available(self):
        return REAL_API_AVAILABLE

    def get_status(self):
        return {
            "asset_type": "water_pump",
            "source": self.source_name,
            "realtime_available": REAL_API_AVAILABLE,
            "model_status": self.model_status,
            "status": "LIVE_IOT" if REAL_API_AVAILABLE else "HISTORICAL_DATASET",
            "protocol": "OPC-UA / MQTT" if REAL_API_AVAILABLE else "Dataset Adapter",
            "warning": "Water-pump signal is decision-support only due to out-of-time validation limitations."
        }

    def get_current_data(self, pump_sample=None):
        if REAL_API_AVAILABLE:
            try:
                headers = {"Authorization": f"Bearer {WATER_PUMP_API_KEY}"} if WATER_PUMP_API_KEY else {}
                res = requests.get(WATER_PUMP_API_URL, headers=headers, timeout=4)
                if res.status_code == 200:
                    raw_json = res.json()
                    return normalize_asset_telemetry(
                        asset_id="WATER_PUMP_MAIN",
                        asset_type="water_pump",
                        raw_data=raw_json.get("data", {}),
                        source_type="live_iot_api",
                        timestamp_str=raw_json.get("timestamp")
                    )
            except Exception as e:
                print("Live Water Pump API fetch exception, switching to Historical Dataset:", e)

        # Fallback to Historical Dataset Sample
        sample_dict = pump_sample if isinstance(pump_sample, dict) else {}

        return normalize_asset_telemetry(
            asset_id="WATER_PUMP_MAIN",
            asset_type="water_pump",
            raw_data=sample_dict,
            source_type="historical_dataset"
        )

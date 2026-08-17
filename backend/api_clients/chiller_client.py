"""
CascadeGuard AI — HVAC Chiller Telemetry Adapter Client
Phase 10: Real API Integration & Live Data Adapter Architecture

Adapter interface for Commercial HVAC Chiller Telemetry.
Supports live BMS REST API endpoints when configured via environment variables.
When no live BMS endpoint is connected, defaults to Historical Dataset mode.
"""

import os
import requests
from api_clients.schema import normalize_asset_telemetry

CHILLER_API_URL = os.environ.get("CHILLER_API_URL", "").strip()
CHILLER_API_KEY = os.environ.get("CHILLER_API_KEY", "").strip()

REAL_API_AVAILABLE = bool(CHILLER_API_URL)


class ChillerTelemetryClient:
    def __init__(self):
        self.source_name = "live_bms_api" if REAL_API_AVAILABLE else "historical_dataset"

    def get_source(self):
        return self.source_name

    def is_available(self):
        return REAL_API_AVAILABLE

    def get_status(self):
        return {
            "asset_type": "chiller",
            "source": self.source_name,
            "realtime_available": REAL_API_AVAILABLE,
            "status": "LIVE_BMS" if REAL_API_AVAILABLE else "HISTORICAL_DATASET",
            "protocol": "BACnet IP / Modbus TCP" if REAL_API_AVAILABLE else "Dataset Adapter",
            "warning": None if REAL_API_AVAILABLE else "No live BMS API connected. Operating in Historical Dataset Mode."
        }

    def get_current_data(self, chiller_sample=None):
        if REAL_API_AVAILABLE:
            try:
                headers = {"Authorization": f"Bearer {CHILLER_API_KEY}"} if CHILLER_API_KEY else {}
                res = requests.get(CHILLER_API_URL, headers=headers, timeout=4)
                if res.status_code == 200:
                    raw_json = res.json()
                    return normalize_asset_telemetry(
                        asset_id="CHILLER_MAIN",
                        asset_type="chiller",
                        raw_data=raw_json.get("data", {}),
                        source_type="live_bms_api",
                        timestamp_str=raw_json.get("timestamp")
                    )
            except Exception as e:
                print("Live BMS API fetch exception, switching to Historical Dataset:", e)

        # Fallback to Historical Dataset Sample
        sample_dict = chiller_sample if isinstance(chiller_sample, dict) else {}

        return normalize_asset_telemetry(
            asset_id="CHILLER_MAIN",
            asset_type="chiller",
            raw_data=sample_dict,
            source_type="historical_dataset"
        )

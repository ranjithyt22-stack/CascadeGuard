"""
CascadeGuard AI — Power Transformer Telemetry Adapter Client
Phase 10: Real API Integration & Live Data Adapter Architecture

Adapter interface for Substation Transformer Telemetry.
Supports live industrial SCADA / OPC-UA REST API endpoints when configured via environment variables.
When no live industrial endpoint is connected, defaults to Historical Stream Replay.
"""

import os
import requests
from api_clients.schema import normalize_asset_telemetry

TRANSFORMER_API_URL = os.environ.get("TRANSFORMER_API_URL", "").strip()
TRANSFORMER_API_KEY = os.environ.get("TRANSFORMER_API_KEY", "").strip()

REAL_API_AVAILABLE = bool(TRANSFORMER_API_URL)


class TransformerTelemetryClient:
    def __init__(self):
        self.source_name = "live_scada_api" if REAL_API_AVAILABLE else "historical_replay"

    def get_source(self):
        return self.source_name

    def is_available(self):
        return REAL_API_AVAILABLE

    def get_status(self):
        return {
            "asset_type": "transformer",
            "source": self.source_name,
            "realtime_available": REAL_API_AVAILABLE,
            "status": "LIVE_SCADA" if REAL_API_AVAILABLE else "HISTORICAL_REPLAY",
            "protocol": "IEC 61850 / DNP3" if REAL_API_AVAILABLE else "Stream Replay Adapter",
            "warning": None if REAL_API_AVAILABLE else "No live SCADA API connected. Operating in Historical Telemetry Replay Mode."
        }

    def get_current_data(self, tx_id="TX-001", replay_sample=None):
        if REAL_API_AVAILABLE:
            try:
                headers = {"Authorization": f"Bearer {TRANSFORMER_API_KEY}"} if TRANSFORMER_API_KEY else {}
                url = f"{TRANSFORMER_API_URL}?tx_id={tx_id}"
                res = requests.get(url, headers=headers, timeout=4)
                if res.status_code == 200:
                    raw_json = res.json()
                    return normalize_asset_telemetry(
                        asset_id=tx_id,
                        asset_type="transformer",
                        raw_data=raw_json.get("data", {}),
                        source_type="live_scada_api",
                        timestamp_str=raw_json.get("timestamp")
                    )
            except Exception as e:
                print("Live SCADA API fetch exception, switching to Historical Replay:", e)

        # Fallback to Historical Replay
        sample_dict = replay_sample if replay_sample else {}
        ts = sample_dict.get("timestamp") if isinstance(sample_dict, dict) else None

        return normalize_asset_telemetry(
            asset_id=tx_id,
            asset_type="transformer",
            raw_data=sample_dict,
            source_type="historical_replay",
            timestamp_str=ts
        )

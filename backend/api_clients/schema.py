"""
CascadeGuard AI — Unified Real-Time Data Schema & Data Freshness Module
Phase 10: Real API Integration & Live Data Adapter Architecture

Normalizes raw asset telemetry from any source (Live API, Industrial SCADA, BMS, or Historical Replay)
into a standardized structure with explicit data quality and freshness tracking.
"""

import time
from datetime import datetime, timezone
import pandas as pd


def calculate_data_freshness(timestamp_str, is_historical=False, source_type="api"):
    if is_historical or source_type in ["historical_replay", "historical_dataset"]:
        return {
            "status": "HISTORICAL_REPLAY" if source_type == "historical_replay" else "HISTORICAL_DATASET",
            "age_seconds": None,
            "stale": False,
            "is_live": False,
            "label": "HISTORICAL REPLAY" if source_type == "historical_replay" else "HISTORICAL DATASET"
        }

    if not timestamp_str:
        return {
            "status": "UNKNOWN",
            "age_seconds": None,
            "stale": True,
            "is_live": False,
            "label": "NO TIMESTAMP"
        }

    try:
        dt = pd.to_datetime(timestamp_str, errors="coerce")
        if pd.isna(dt):
            raise ValueError("Invalid timestamp")

        now = pd.Timestamp.now()
        age_sec = abs((now - dt).total_seconds())

        if age_sec < 60.0:
            status = "LIVE"
            stale = False
            label = "LIVE API"
        elif age_sec <= 300.0:
            status = "RECENT"
            stale = False
            label = "RECENT API (< 5m)"
        else:
            status = "STALE"
            stale = True
            label = f"STALE API ({int(age_sec // 60)}m old)"

        return {
            "status": status,
            "age_seconds": round(float(age_sec), 1),
            "stale": stale,
            "is_live": (status == "LIVE"),
            "label": label
        }

    except Exception:
        return {
            "status": "UNKNOWN",
            "age_seconds": None,
            "stale": True,
            "is_live": False,
            "label": "UNKNOWN AGE"
        }


def normalize_asset_telemetry(asset_id, asset_type, raw_data, source_type, timestamp_str=None, missing_fields=None):
    is_hist = source_type in ["historical_replay", "historical_dataset"]
    is_realtime = not is_hist and bool(raw_data)

    freshness = calculate_data_freshness(timestamp_str, is_historical=is_hist, source_type=source_type)

    return {
        "asset_id": str(asset_id),
        "asset_type": str(asset_type),
        "timestamp": timestamp_str or time.strftime("%Y-%m-%d %H:%M:%S"),
        "source": str(source_type),
        "realtime": is_realtime,
        "data": raw_data or {},
        "quality": {
            "available": bool(raw_data),
            "missing_fields": missing_fields or [],
            "stale": freshness["stale"],
            "freshness_status": freshness["status"],
            "freshness_label": freshness["label"],
            "age_seconds": freshness["age_seconds"]
        }
    }

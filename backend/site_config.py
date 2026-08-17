"""
CascadeGuard AI — Precise Infrastructure Site Location & Configuration Schema
Phase 11A & Phase 11: Precise Infrastructure Site Location, Configuration & Climate Thresholds

Validates and manages site-specific infrastructure configuration (Site ID, Site Name, Exact Coordinates, Asset IDs, Climate Thresholds).
"""

import copy

DEFAULT_SITE_CONFIG = {
    "site_id": "SITE-001",
    "site_name": "Coimbatore Industrial Facility",
    "location": {
        "name": "Coimbatore",
        "latitude": 11.00555,
        "longitude": 76.96612
    },
    "assets": {
        "transformer_id": "TX-001",
        "chiller_id": "CH-001",
        "water_pump_id": "WP-001"
    },
    "climate_thresholds": {
        "heatwave_threshold_temp": 35.0,
        "heatwave_threshold_hours": 3
    },
    "risk_thresholds": {
        "watch": 25.0,
        "warning": 50.0,
        "critical": 75.0
    }
}

ACTIVE_SITE_CONFIG = copy.deepcopy(DEFAULT_SITE_CONFIG)


def get_risk_thresholds():
    """Returns configured risk thresholds dict."""
    return ACTIVE_SITE_CONFIG.get("risk_thresholds", {
        "watch": 25.0,
        "warning": 50.0,
        "critical": 75.0
    })


def validate_site_config(data):
    if not isinstance(data, dict):
        return False, "Payload must be a JSON object", None

    site_id = str(data.get("site_id", "")).strip()
    if not site_id:
        return False, "Missing required parameter: site_id", None

    site_name = str(data.get("site_name", "")).strip()
    if not site_name:
        return False, "Missing required parameter: site_name", None

    # Latitude validation
    try:
        lat = float(data.get("latitude"))
        if not (-90.0 <= lat <= 90.0):
            return False, f"Invalid latitude ({lat}). Latitude must be between -90 and 90 degrees.", None
    except (ValueError, TypeError):
        return False, "Invalid latitude value. Latitude must be a numeric float.", None

    # Longitude validation
    try:
        lon = float(data.get("longitude"))
        if not (-180.0 <= lon <= 180.0):
            return False, f"Invalid longitude ({lon}). Longitude must be between -180 and 180 degrees.", None
    except (ValueError, TypeError):
        return False, "Invalid longitude value. Longitude must be a numeric float.", None

    # Asset ID validations
    tx_id = str(data.get("transformer_id", "TX-001")).strip()
    ch_id = str(data.get("chiller_id", "CH-001")).strip()
    wp_id = str(data.get("water_pump_id", "WP-001")).strip()

    if not tx_id:
        return False, "Missing required parameter: transformer_id", None
    if not ch_id:
        return False, "Missing required parameter: chiller_id", None
    if not wp_id:
        return False, "Missing required parameter: water_pump_id", None

    try:
        thresh_temp = float(data.get("heatwave_threshold_temp", 35.0))
        thresh_hrs = int(data.get("heatwave_threshold_hours", 3))
    except (ValueError, TypeError):
        thresh_temp = 35.0
        thresh_hrs = 3

    normalized_site = {
        "site_id": site_id,
        "site_name": site_name,
        "location": {
            "name": data.get("location_name", site_name.split()[0] if site_name else "Custom Site"),
            "latitude": round(lat, 5),
            "longitude": round(lon, 5)
        },
        "assets": {
            "transformer_id": tx_id,
            "chiller_id": ch_id,
            "water_pump_id": wp_id
        },
        "climate_thresholds": {
            "heatwave_threshold_temp": round(thresh_temp, 1),
            "heatwave_threshold_hours": max(1, thresh_hrs)
        }
    }

    return True, None, normalized_site


def get_active_site_config():
    return ACTIVE_SITE_CONFIG


def set_active_site_config(new_site):
    global ACTIVE_SITE_CONFIG
    ACTIVE_SITE_CONFIG = new_site
    return ACTIVE_SITE_CONFIG

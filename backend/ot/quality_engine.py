"""
backend/ot/quality_engine.py
============================
Sensor quality validation engine. Validates limits, checks for stuck sensors,
detects stale updates, and formats validation diagnostics.
"""
import time
from collections import deque
import threading

# Cache to store last 5 values per (device_id, measurement) for stuck sensor checks
value_history = {}
history_lock = threading.Lock()

# Standard operating bounds
OPERATING_BOUNDS = {
    "transformer": {
        "OTI": (-40.0, 150.0),
        "WTI": (-40.0, 160.0),
        "load_percent": (0.0, 300.0),
        "current": (0.0, 5000.0),
        "voltage": (0.0, 50000.0),
        "power": (0.0, 10000.0)
    },
    "chiller": {
        "compressor_current": (0.0, 1000.0),
        "kW": (0.0, 5000.0),
        "cooling_load": (0.0, 100.0),
        "TEO": (-30.0, 80.0),
        "TEI": (-30.0, 80.0),
        "condenser_temperature": (-30.0, 100.0),
        "evaporator_temperature": (-30.0, 80.0),
        "flow_rate": (0.0, 1000.0),
        "cop": (0.0, 15.0)
    },
    "water_pump": {
        "motor_current": (0.0, 500.0),
        "motor_power": (0.0, 1000.0),
        "motor_temperature": (-40.0, 180.0),
        "vibration": (0.0, 20.0),
        "flow": (0.0, 1000.0),
        "pressure": (0.0, 50.0),
        "rpm": (0.0, 10000.0),
        "efficiency": (0.0, 100.0)
    },
    "environment": {
        "temperature": (-50.0, 65.0),
        "humidity": (0.0, 100.0),
        "pressure": (800.0, 1200.0),
        "rain": (0.0, 500.0),
        "wind": (0.0, 250.0),
        "solar_radiation": (0.0, 2000.0),
        "dew_point": (-50.0, 65.0)
    }
}

def validate_point(device_id: str, asset_type: str, measurement: str, value: float) -> dict:
    """
    Validates a single telemetry measurement point.
    Returns quality diagnostic dict: {"status": "VALID"|"INVALID", "error": None|str}
    """
    atype = asset_type.lower()
    if atype not in OPERATING_BOUNDS:
        return {"status": "VALID", "error": None}
        
    bounds = OPERATING_BOUNDS[atype]
    if measurement not in bounds:
        return {"status": "VALID", "error": None}
        
    min_v, max_v = bounds[measurement]
    if value < min_v or value > max_v:
        return {
            "status": "INVALID",
            "error": f"Value {value} out of operating bounds [{min_v}, {max_v}] for {measurement}"
        }
        
    # Check for stuck sensor
    key = (device_id, measurement)
    with history_lock:
        if key not in value_history:
            value_history[key] = deque(maxlen=5)
        value_history[key].append(value)
        
        history = list(value_history[key])
        if len(history) == 5 and len(set(history)) == 1:
            return {
                "status": "INVALID",
                "error": f"POSSIBLE_SENSOR_STUCK: Sensor value stuck at {value} for last 5 updates"
            }
            
    return {"status": "VALID", "error": None}

def parse_time_freshness(timestamp_str: str) -> str:
    """Checks if timestamp is within the last 30 seconds."""
    try:
        struct_time = time.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        epoch_time = time.mktime(struct_time)
        if time.time() - epoch_time > 30.0:
            return "STALE"
        return "LIVE"
    except Exception:
        return "STALE"

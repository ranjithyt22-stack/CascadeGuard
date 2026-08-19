"""
backend/ot/device_registry.py
=============================
Device registry management. Registers devices, keeps track of attributes,
checks connection statuses, and persists state to JSON.
"""
import json
import time
import threading
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = BASE_DIR / "data" / "device_registry.json"

registry_lock = threading.Lock()

# Initial standard default devices for monitored sites
DEFAULT_DEVICES = [
    # Coimbatore
    {"device_id": "TRF-CBE", "asset_id": "TX-001", "asset_type": "transformer", "location": "CBE-001", "firmware_version": "1.0.0", "protocol": "mqtt", "status": "ONLINE", "telemetry_frequency": 5, "last_seen": "", "sensors": ["oil_temperature", "winding_temperature", "load_percent"]},
    {"device_id": "CHL-CBE", "asset_id": "CH-001", "asset_type": "chiller", "location": "CBE-001", "firmware_version": "1.0.0", "protocol": "mqtt", "status": "ONLINE", "telemetry_frequency": 5, "last_seen": "", "sensors": ["compressor_power", "supply_temperature", "flow_rate"]},
    {"device_id": "PMP-CBE", "asset_id": "WP-001", "asset_type": "water_pump", "location": "CBE-001", "firmware_version": "1.0.0", "protocol": "mqtt", "status": "ONLINE", "telemetry_frequency": 5, "last_seen": "", "sensors": ["motor_temperature", "vibration", "flow_rate"]},
    {"device_id": "ENV-CBE", "asset_id": "ENV-CBE", "asset_type": "environment", "location": "CBE-001", "firmware_version": "1.0.0", "protocol": "mqtt", "status": "ONLINE", "telemetry_frequency": 10, "last_seen": "", "sensors": ["outdoor_temperature", "humidity"]},
    
    # Chennai
    {"device_id": "TRF-CHN", "asset_id": "TR-001", "asset_type": "transformer", "location": "CHN-001", "firmware_version": "1.0.0", "protocol": "mqtt", "status": "ONLINE", "telemetry_frequency": 5, "last_seen": "", "sensors": ["oil_temperature", "winding_temperature", "load_percent"]},
    {"device_id": "CHL-CHN", "asset_id": "CH-001", "asset_type": "chiller", "location": "CHN-001", "firmware_version": "1.0.0", "protocol": "mqtt", "status": "ONLINE", "telemetry_frequency": 5, "last_seen": "", "sensors": ["compressor_power", "supply_temperature", "flow_rate"]},
    {"device_id": "PMP-CHN", "asset_id": "WP-001", "asset_type": "water_pump", "location": "CHN-001", "firmware_version": "1.0.0", "protocol": "mqtt", "status": "ONLINE", "telemetry_frequency": 5, "last_seen": "", "sensors": ["motor_temperature", "vibration", "flow_rate"]},
    {"device_id": "ENV-CHN", "asset_id": "ENV-CHN", "asset_type": "environment", "location": "CHN-001", "firmware_version": "1.0.0", "protocol": "mqtt", "status": "ONLINE", "telemetry_frequency": 10, "last_seen": "", "sensors": ["outdoor_temperature", "humidity"]}
]

class DeviceRegistry:
    def __init__(self):
        self.devices = []
        self.load_registry()

    def load_registry(self):
        with registry_lock:
            if REGISTRY_PATH.exists():
                try:
                    with open(REGISTRY_PATH, "r") as f:
                        self.devices = json.load(f)
                except Exception:
                    self.devices = list(DEFAULT_DEVICES)
            else:
                self.devices = list(DEFAULT_DEVICES)
                self.save_registry_unlocked()

    def save_registry_unlocked(self):
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(REGISTRY_PATH, "w") as f:
                json.dump(self.devices, f, indent=2)
        except Exception as e:
            print("[DeviceRegistry] Save error:", e)

    def save_registry(self):
        with registry_lock:
            self.save_registry_unlocked()

    def get_all_devices(self) -> list:
        # Dynamically refresh status based on last seen time
        now = time.time()
        with registry_lock:
            for dev in self.devices:
                ls = dev.get("last_seen", "")
                if not ls:
                    dev["status"] = "OFFLINE"
                    continue
                try:
                    struct_t = time.strptime(ls, "%Y-%m-%d %H:%M:%S")
                    diff = now - time.mktime(struct_t)
                    if diff > 60.0:
                        dev["status"] = "OFFLINE"
                    elif diff > 30.0:
                        dev["status"] = "STALE"
                    else:
                        dev["status"] = "ONLINE"
                except Exception:
                    dev["status"] = "OFFLINE"
            return list(self.devices)

    def get_device(self, device_id: str) -> dict:
        devices = self.get_all_devices()
        for dev in devices:
            if dev["device_id"] == device_id:
                return dev
        return None

    def update_heartbeat(self, device_id: str, firmware: str = None, signal: int = 100):
        with registry_lock:
            for dev in self.devices:
                if dev["device_id"] == device_id:
                    dev["last_seen"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    dev["status"] = "ONLINE"
                    if firmware:
                        dev["firmware_version"] = firmware
                    dev["signal_quality"] = signal
                    self.save_registry_unlocked()
                    break

    def add_device(self, device_dict: dict) -> bool:
        with registry_lock:
            for dev in self.devices:
                if dev["device_id"] == device_dict["device_id"]:
                    return False  # Already registered
            device_dict["last_seen"] = ""
            device_dict["status"] = "OFFLINE"
            self.devices.append(device_dict)
            self.save_registry_unlocked()
            return True

"""
backend/ot/mqtt_client.py
=========================
Async MQTT subscriber client for CascadeGuard IoT Ingestion.
Listens to topic streams, validates quality, normalizes data, and stores points.
"""
import os
import json
import time
import threading
from typing import Dict, Any
import paho.mqtt.client as mqtt

from ot.quality_engine import validate_point
from ot.providers import TelemetryNormalizer
from ot.ts_storage import insert_telemetry_point
from ot.device_registry import DeviceRegistry

# In-memory edge offline buffer for resilience
offline_buffer = []
buffer_lock = threading.Lock()

class CascadeGuardMQTTClient:
    def __init__(self, registry: DeviceRegistry):
        self.registry = registry
        self.broker = os.environ.get("MQTT_BROKER", "127.0.0.1")
        self.port = int(os.environ.get("MQTT_PORT", 1883))
        self.username = os.environ.get("MQTT_USERNAME", "")
        self.password = os.environ.get("MQTT_PASSWORD", "")
        
        self.client = None
        self.is_connected = False
        self.client_thread = None

    def connect(self):
        """Starts the MQTT loop in a background thread."""
        try:
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            if self.username:
                self.client.username_pw_set(self.username, self.password)
                
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            self.client.on_message = self.on_message
            
            self.client_thread = threading.Thread(target=self._run_loop, daemon=True)
            self.client_thread.start()
            print(f"[MQTTClient] Background service started. Broker: {self.broker}:{self.port}")
        except Exception as e:
            print(f"[MQTTClient] Initialization failed: {e}")

    def _run_loop(self):
        while True:
            try:
                if not self.is_connected:
                    print(f"[MQTTClient] Connecting to broker {self.broker}:{self.port}...")
                    self.client.connect(self.broker, self.port, keepalive=60)
                    self.client.loop_forever()
            except Exception as e:
                print(f"[MQTTClient] Loop exception: {e}. Retrying in 5 seconds...")
                self.is_connected = False
                time.sleep(5)

    def on_connect(self, client, userdata, flags, rc, properties=None):
        print(f"[MQTTClient] Connected to broker successfully. (rc={rc})")
        self.is_connected = True
        
        # Subscribe to telemetry topics
        self.client.subscribe("cascadeguard/facility/+/+/+/telemetry")
        self.client.subscribe("cascadeguard/+/+/heartbeat")
        
        # Replay buffered offline messages
        self.replay_buffer()

    def on_disconnect(self, client, userdata, flags, rc, properties=None):
        print(f"[MQTTClient] Disconnected from broker. (rc={rc})")
        self.is_connected = False

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            topic_parts = msg.topic.split("/")
            
            # Topic: cascadeguard/facility/{facility_id}/{asset_type}/{device_id}/telemetry
            if len(topic_parts) == 6 and topic_parts[5] == "telemetry":
                site_id = topic_parts[2]
                asset_type = topic_parts[3]
                device_id = topic_parts[4]
                
                self.process_raw_telemetry(site_id, asset_type, device_id, payload)
                
            # Topic: cascadeguard/{device_id}/heartbeat
            elif len(topic_parts) == 3 and topic_parts[2] == "heartbeat":
                device_id = topic_parts[1]
                self.registry.update_heartbeat(device_id)
        except Exception as e:
            print(f"[MQTTClient] Failed to process message on {msg.topic}: {e}")

    def process_raw_telemetry(self, site_id: str, asset_type: str, device_id: str, payload: Dict[str, Any]):
        """Processes and stores a telemetry payload."""
        measurements = payload.get("measurements", {})
        source = payload.get("source", "hardware")
        timestamp = payload.get("timestamp") or time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Update heartbeat
        self.registry.update_heartbeat(device_id)
        
        # Fetch asset mapping
        device_info = self.registry.get_device(device_id)
        asset_id = device_info.get("asset_id", "UNKNOWN-ASSET") if device_info else "UNKNOWN-ASSET"
        
        # Normalize fields
        atype = asset_type.lower()
        if atype == "transformer":
            norm = TelemetryNormalizer.normalize_transformer(measurements)
            units = {"OTI": "°C", "WTI": "°C", "ATI": "°C", "OLI": "%", "VL1": "V", "VL2": "V", "VL3": "V", "IL1": "A", "IL2": "A", "IL3": "A", "KW": "kW"}
        elif atype == "chiller":
            norm = TelemetryNormalizer.normalize_chiller(measurements)
            units = {"TEI": "°C", "TEO": "°C", "TCI": "°C", "TCO": "°C", "kW": "kW"}
        elif atype == "water_pump":
            norm = TelemetryNormalizer.normalize_pump(measurements)
            units = {"flow": "L/s", "pressure": "bar", "motor_temperature": "°C", "vibration": "mm/s"}
        elif atype == "environment":
            norm = TelemetryNormalizer.normalize_environment(measurements)
            units = {"temperature": "°C", "humidity": "%", "rain": "mm", "wind": "km/h"}
        else:
            return

        # Validate and store
        for measurement, val in norm.items():
            diag = validate_point(device_id, asset_type, measurement, val)
            quality = diag["status"]
            
            # If not connected to network, save to edge buffer
            if not self.is_connected:
                with buffer_lock:
                    offline_buffer.append((timestamp, device_id, asset_id, asset_type, measurement, val, units.get(measurement, ""), quality, source))
            else:
                insert_telemetry_point(
                    timestamp=timestamp,
                    device_id=device_id,
                    asset_id=asset_id,
                    asset_type=asset_type.upper(),
                    measurement=measurement,
                    value=val,
                    unit=units.get(measurement, ""),
                    quality=quality,
                    source=source
                )

    def replay_buffer(self):
        """Flushes in-memory offline buffers to database upon connection."""
        with buffer_lock:
            global offline_buffer
            if not offline_buffer:
                return
            print(f"[MQTTClient] Replaying {len(offline_buffer)} offline buffered telemetry points...")
            for pt in offline_buffer:
                insert_telemetry_point(*pt)
            offline_buffer.clear()

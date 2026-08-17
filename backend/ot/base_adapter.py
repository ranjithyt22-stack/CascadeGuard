"""
CascadeGuard AI — Base Industrial Telemetry Adapter Interface
Phase 12: Real-Time Industrial OT Connectivity + Telemetry Simulation

Defines the common interface and unified telemetry schema for all OT adapters
(Modbus TCP, OPC-UA, MQTT, and Mock Generator).
"""

from abc import ABC, abstractmethod
import time


class BaseTelemetryAdapter(ABC):
    def __init__(self, asset_id, asset_type, source_name):
        self.asset_id = asset_id
        self.asset_type = asset_type.upper()  # TRANSFORMER, CHILLER, WATER_PUMP
        self.source_name = source_name
        self.mode = "MOCK"  # REAL_OT | MOCK
        self.connection_status = "DISCONNECTED"  # CONNECTED | DISCONNECTED | SIMULATED

    @abstractmethod
    def connect(self):
        """Establishes connection to physical/virtual OT endpoint."""
        pass

    @abstractmethod
    def disconnect(self):
        """Closes connection to OT endpoint."""
        pass

    @abstractmethod
    def read_telemetry(self):
        """Reads raw asset telemetry and returns standardized schema dict."""
        pass

    @abstractmethod
    def health_check(self):
        """Returns True if connection is active and healthy."""
        pass

    def get_status(self):
        """Returns standardized adapter metadata dictionary."""
        return {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "source": self.source_name,
            "mode": self.mode,
            "connection_status": self.connection_status,
            "is_healthy": self.health_check()
        }

    def format_telemetry_schema(self, telemetry_data, quality_data=None):
        """Formats telemetry data into the unified CascadeGuard telemetry schema."""
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        if quality_data is None:
            quality_data = {
                "complete": True,
                "missing_fields": [],
                "validation_errors": []
            }

        # Calculate freshness
        freshness = "LIVE" if self.connection_status == "CONNECTED" else ("HISTORICAL" if self.mode == "HISTORICAL" else "RECENT")

        return {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "timestamp": now_str,
            "source": self.source_name,
            "mode": self.mode,
            "freshness": freshness,
            "connection_status": self.connection_status,
            "data_quality": quality_data,
            "telemetry": telemetry_data
        }

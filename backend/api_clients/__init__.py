"""
CascadeGuard AI — API Clients Package
Phase 10: Real API Integration & Live Data Adapter Architecture
"""

from api_clients.weather_client import WeatherAPIClient
from api_clients.transformer_client import TransformerTelemetryClient
from api_clients.chiller_client import ChillerTelemetryClient
from api_clients.water_pump_client import WaterPumpTelemetryClient
from api_clients.schema import normalize_asset_telemetry, calculate_data_freshness

__all__ = [
    "WeatherAPIClient",
    "TransformerTelemetryClient",
    "ChillerTelemetryClient",
    "WaterPumpTelemetryClient",
    "normalize_asset_telemetry",
    "calculate_data_freshness"
]

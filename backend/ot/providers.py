"""
backend/ot/providers.py
========================
SI/Standard Unit normalizers and conditional data multiplexers.
Translates raw sensor telemetry into internal SI standards.
"""
from typing import Dict, Any

class TelemetryNormalizer:
    @staticmethod
    def normalize_transformer(measurements: Dict[str, Any]) -> Dict[str, Any]:
        """Normalizes transformer parameters to standard OTI, WTI, ATI, current, power."""
        return {
            "OTI": round(float(measurements.get("oil_temperature", measurements.get("OTI", 50.0))), 2),
            "WTI": round(float(measurements.get("winding_temperature", measurements.get("WTI", 56.0))), 2),
            "ATI": round(float(measurements.get("ambient_temperature", measurements.get("ATI", 30.0))), 2),
            "OLI": round(float(measurements.get("oil_level", measurements.get("OLI", 85.0))), 2),
            "VL1": round(float(measurements.get("voltage", measurements.get("VL1", 11.02))), 2),
            "VL2": round(float(measurements.get("voltage", measurements.get("VL2", 11.02))), 2),
            "VL3": round(float(measurements.get("voltage", measurements.get("VL3", 11.02))), 2),
            "IL1": round(float(measurements.get("current", measurements.get("IL1", 420.0))), 1),
            "IL2": round(float(measurements.get("current", measurements.get("IL2", 420.0))), 1),
            "IL3": round(float(measurements.get("current", measurements.get("IL3", 420.0))), 1),
            "KW": round(float(measurements.get("power", measurements.get("KW", 800.0))), 1)
        }

    @staticmethod
    def normalize_chiller(measurements: Dict[str, Any]) -> Dict[str, Any]:
        """Normalizes chiller parameters to standard TEI, TEO, TCI, TCO, kW."""
        return {
            "TEI": round(float(measurements.get("return_temperature", measurements.get("TEI", 12.0))), 2),
            "TEO": round(float(measurements.get("supply_temperature", measurements.get("TEO", 7.0))), 2),
            "TCI": round(float(measurements.get("condenser_inlet_temperature", measurements.get("TCI", 28.0))), 2),
            "TCO": round(float(measurements.get("condenser_outlet_temperature", measurements.get("TCO", 33.0))), 2),
            "kW": round(float(measurements.get("compressor_power", measurements.get("kW", measurements.get("kW_draw", 180.0)))), 1)
        }

    @staticmethod
    def normalize_pump(measurements: Dict[str, Any]) -> Dict[str, Any]:
        """Normalizes water pump parameters to standard flow, pressure, motor_temperature, vibration."""
        return {
            "flow": round(float(measurements.get("flow_rate", measurements.get("flow", 125.0))), 2),
            "pressure": round(float(measurements.get("pressure", 4.2)), 2),
            "motor_temperature": round(float(measurements.get("motor_temperature", 48.0)), 2),
            "vibration": round(float(measurements.get("vibration", 1.5)), 2)
        }

    @staticmethod
    def normalize_environment(measurements: Dict[str, Any]) -> Dict[str, Any]:
        """Normalizes environmental weather parameters."""
        return {
            "temperature": round(float(measurements.get("outdoor_temperature", measurements.get("temperature", 28.5))), 1),
            "humidity": round(float(measurements.get("humidity", 60.0)), 1),
            "rain": round(float(measurements.get("rainfall", measurements.get("rain", 0.0))), 1),
            "wind": round(float(measurements.get("wind_speed", measurements.get("wind", 12.0))), 1)
        }

class EnvironmentDataProvider:
    @staticmethod
    def get_merged_weather(site_id: str, weather_api_data: Dict[str, Any], local_sensor_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Merges external weather API with local physical environmental sensors.
        Detects significant discrepancy errors if they differ by > 5.0 °C.
        """
        api_temp = float(weather_api_data.get("temperature", 28.5))
        api_hum = float(weather_api_data.get("humidity", 60.0))
        api_rain = float(weather_api_data.get("rain", 0.0))
        api_wind = float(weather_api_data.get("wind", 12.0))
        api_stress = float(weather_api_data.get("climate_stress", 30.0))

        # Default fallback is WEATHER_API
        source = "WEATHER_API"
        temp = api_temp
        hum = api_hum
        rain = api_rain
        wind = api_wind
        discrepancy = None

        if local_sensor_data and len(local_sensor_data) > 0:
            local_temp = float(local_sensor_data.get("outdoor_temperature", local_sensor_data.get("temperature", api_temp)))
            local_hum = float(local_sensor_data.get("humidity", api_hum))
            local_rain = float(local_sensor_data.get("rainfall", local_sensor_data.get("rain", api_rain)))
            local_wind = float(local_sensor_data.get("wind_speed", local_sensor_data.get("wind", api_wind)))

            # Discrepancy comparison
            if abs(local_temp - api_temp) > 5.0:
                discrepancy = f"DISCREPANCY_DETECTED: Local temp ({local_temp}°C) differs from API weather ({api_temp}°C) by > 5.0°C"

            source = "LOCAL_SENSOR_DATA"
            temp = local_temp
            hum = local_hum
            rain = local_rain
            wind = local_wind

        return {
            "temperature": temp,
            "humidity": hum,
            "rain": rain,
            "wind": wind,
            "climate_stress": api_stress, # Weather API remains source of climate stress
            "source": source,
            "discrepancy": discrepancy
        }

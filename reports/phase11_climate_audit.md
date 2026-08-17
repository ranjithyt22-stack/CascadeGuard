# CascadeGuard AI — Climate Implementation Audit (Phase 11)

This report documents the existing climate architecture, formulas, forecast parameters, data flow, and frontend display in CascadeGuard AI **BEFORE** implementing the Phase 11 Climate Intelligence & Confidence Layer.

---

## 1. CURRENT OPEN-METEO WEATHER API FIELDS
Currently, `WeatherAPIClient` (`backend/api_clients/weather_client.py`) fetches 3 days of 1-hour forecast data from Open-Meteo REST API (`https://api.open-meteo.com/v1/forecast`):
- `temperature_2m` ($^\circ\text{C}$)
- `relative_humidity_2m` ($\%$)
- `precipitation` (mm)
- `wind_speed_10m` (km/h)

---

## 2. CURRENT CLIMATE STRESS FORMULA
The climate stress index is calculated across hourly forecast rows as:
$$\text{HeatStress} = \text{clip}\left(\frac{T - 30.0}{15.0} \times 100, 0, 100\right)$$
$$\text{HumidityStress} = \text{clip}\left(\frac{H - 60.0}{40.0} \times 100, 0, 100\right)$$
$$\text{RainStress} = \text{clip}\left(\frac{\text{Precipitation}}{20.0} \times 100, 0, 100\right)$$
$$\text{WindStress} = \text{clip}\left(\frac{\text{Wind} - 30.0}{40.0} \times 100, 0, 100\right)$$
$$\text{ClimateStress} = 0.45 \times \text{HeatStress} + 0.20 \times \text{HumidityStress} + 0.20 \times \text{RainStress} + 0.15 \times \text{WindStress}$$

Peak `climate_stress` over the 72-hour forecast horizon is returned as the overall `climate_stress` score.

---

## 3. ASSET CASCADE COUPLING
In `backend/cascade_graph.py`, asset risks are aggregated into System Cascade Risk:
$$\text{SystemAssetRisk} = 0.50 \times \text{TransformerRisk} + 0.30 \times \text{ChillerRisk} + 0.20 \times \text{PumpRisk}$$
$$\text{SystemCascadeRisk} = \text{clip}(0.80 \times \text{SystemAssetRisk} + 0.20 \times \text{ClimateStress}, 0, 100)$$

Currently:
- The single generic `climate_stress` score is applied identically across all assets.
- Heatwave duration (sustained thermal stress over multiple consecutive hours) is not tracked.
- Trend progression (Rising/Stable/Falling) over 6h and 24h horizons is not calculated.
- Data confidence / freshness layer for climate is not explicitly surfaced in a dedicated endpoint.

---

## 4. SCIENTIFIC & DISCLOSURE REQUIREMENTS FOR UPGRADE
1. **Heatwave Duration**: Track sustained hot hours above configurable site threshold $T_{\text{thresh}}$ (default $35.0^\circ\text{C}$).
2. **Asset-Specific Climate Impact**:
   - Power Transformer: Ambient Temperature, Sustained Duration, Humidity, Wind.
   - HVAC Chiller: Ambient Temperature, Humidity, Sustained Duration.
   - Water Pump: Ambient Temperature, Sustained Duration, Humidity.
3. **Non-Causal Engineering Wording**: Explicitly label all climate impact scores as *decision-support engineering indicators*, using wording like `may increase`, `could contribute`, `potential stress`.
4. **Data Confidence**: Label Open-Meteo data as `LIVE` ($<60\text{s}$), `RECENT`, `STALE`, or `FALLBACK` with confidence rating (`HIGH`, `MEDIUM`, `LOW`).

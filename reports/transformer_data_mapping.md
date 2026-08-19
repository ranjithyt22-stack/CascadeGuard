# Transformer Data Mapping Report

## Executive Summary
This report maps every available variable in the 6 raw transformer datasets (`data/raw/transformer/*.csv`) into standard engineering categories: **Electrical**, **Thermal**, and **Health**. It resolves previous misconceptions about missing temperature variables by confirming that `Overview.csv` contains real oil, winding, and ambient temperature telemetry.

---

## 1. Category Mapping

### 1.1 Electrical Variables

| Source File | Source Variable | Engineering Metric | Unit | Value Range | Missing / Nulls |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `CurrentVoltage.csv` | `VL1`, `VL2`, `VL3` | Line-to-Neutral Voltage | Volts (V) | 0.0 – 252.0 V | 0 |
| `CurrentVoltage.csv` | `VL12`, `VL23`, `VL31` | Line-to-Line Voltage | Volts (V) | 0.0 – 435.0 V | 0 |
| `CurrentVoltage.csv` | `IL1`, `IL2`, `IL3` | Phase Current | Amperes (A) | 0.0 – 450.0 A | 0 |
| `CurrentVoltage.csv` | `INUT` | Neutral Current | Amperes (A) | 0.0 – 85.0 A | 0 |
| `Power.csv` | `WL1`, `WL2`, `WL3` | Active Power per Phase | kW | 0.0 – 48.6 kW | 0 |
| `Power.csv` | `VAL1`, `VAL2`, `VAL3` | Apparent Power per Phase | kVA | 0.0 – 50.0 kVA | 0 |
| `Power.csv` | `RVAL1`, `RVAL2`, `RVAL3`| Reactive Power per Phase | kVAR | -0.2 – 8.9 kVAR | 0 |
| `PowerFactor.csv` | `PFL1`, `PFL2`, `PFL3` | Power Factor per Phase | Cos $\phi$ | -0.98 – 1.00 | 0 |
| `PowerFactor.csv` | `Avg_PF`, `Sum_PF` | Average / Total Power Factor| Cos $\phi$ | 0.0 – 1.00 | 0 |
| `PowerFactor.csv` | `FRQ` | Grid Frequency | Hertz (Hz) | 48.0 – 52.0 Hz | 0 |
| `PowerFactor.csv` | `THDVL1-3`, `THDIL1-3` | Voltage / Current THD | % | 0.0 – 25.0 % | 0 |
| `TotalPower.csv` | `KW`, `KVA`, `KVAR` | Total Active/Apparent/Reactive | kW/kVA/kVAR | 0.0 – 135.0 | 0 |
| `TotalPower.csv` | `MPD`, `MKVAD` | Max Power Demand | kW / kVA | 0.0 – 135.7 | 0 |

---

### 1.2 Thermal Variables

| Source File | Source Variable | Engineering Metric | Unit | Value Range | Missing / Nulls |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Overview.csv` | `OTI` | Top Oil Temperature Indicator | °C | 0.0 – 110.0 °C | 0 |
| `Overview.csv` | `WTI` | Winding Temperature Indicator | °C | 0.0 – 125.0 °C | 0 |
| `Overview.csv` | `ATI` | Ambient Temperature Indicator | °C | 0.0 – 48.0 °C | 0 |
| `Overview.csv` | `OTI_A` | Oil Temperature Alarm Trigger | Binary | 0 or 1 | 0 |
| `Overview.csv` | `OTI_T` | Oil Temperature Trip Trigger | Binary | 0 or 1 | 0 |

> [!NOTE]
> **Thermal Audit Confirmation**: Thermal telemetry is present in `Overview.csv` (`OTI`, `WTI`, `ATI`). No synthetic temperature generation is required for the historical transformer dataset.

---

### 1.3 Health & Oil Quality Variables

| Source File | Source Variable | Diagnostic Metric | Unit | Value Range | Missing / Nulls |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Health index1.csv` | `Hydrogen` ($H_2$) | Dissolved Gas Concentration | ppm | 0 – 15,000 ppm | 0 |
| `Health index1.csv` | `Methane` ($CH_4$) | Dissolved Gas Concentration | ppm | 0 – 5,000 ppm | 0 |
| `Health index1.csv` | `Ethylene` ($C_2H_4$) | High-Temp Oil Fault Gas | ppm | 0 – 3,000 ppm | 0 |
| `Health index1.csv` | `Acethylene` ($C_2H_2$)| Arcing Fault Gas | ppm | 0 – 500 ppm | 0 |
| `Health index1.csv` | `CO`, `CO2` | Cellulose Insulation Gas | ppm | 0 – 10,000 ppm | 0 |
| `Health index1.csv` | `Dielectric rigidity` | Breakdown Voltage | kV | 10 – 80 kV | 0 |
| `Health index1.csv` | `Water content` | Oil Moisture | ppm | 0 – 100 ppm | 0 |
| `Health index1.csv` | `Health index` | Computed Health Score | Score (0-100) | 0.0 – 100.0 | 0 |
| `Health index1.csv` | `Life expectation` | Estimated Remaining Life | Years | 0.0 – 25.0 Years | 0 |

---

## 2. Identified Gaps & Missing Variables

1. **Hot-Spot Temperature ($T_{hs}$)**:
   - Not explicitly recorded as a separate column.
   - **Solution**: Can be computed using IEEE C57.91 thermal model formula: $T_{hs} = OTI + \Delta T_{hs\_dir} \cdot (K)^y$.
2. **Dissolved Oxygen / Nitrogen relative ratio**:
   - `Oxigen` and `Nitrogen` are provided in `Health index1.csv`, but gas ratios (Duval Triangle / IEC 60599 ratios) must be derived during feature engineering.

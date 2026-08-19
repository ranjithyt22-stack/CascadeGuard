# HVAC Chiller Data Mapping Report

## Executive Summary
This report details the variable mapping for `data/raw/chiller/11000.xlsx`. The dataset contains 11,000 steady-state operational samples across 16 sensor features and 1 multiclass fault target label (`label`).

---

## 1. Variable Mapping Table

| Variable Name | Standard Engineering Term | Category | Unit | Operational Range |
| :--- | :--- | :--- | :--- | :--- |
| `TEI` | Evaporator Entering Water Temperature | Thermal / Hydraulic | °F | 40.0 – 70.0 °F |
| `TEO` | Evaporator Leaving Water Temperature | Thermal / Hydraulic | °F | 38.0 – 65.0 °F |
| `TCI` | Condenser Entering Water Temperature | Thermal / Hydraulic | °F | 60.0 – 95.0 °F |
| `TCO` | Condenser Leaving Water Temperature | Thermal / Hydraulic | °F | 65.0 – 105.0 °F |
| `kW` | Chiller Compressor Electrical Power | Electrical | kW | 15.0 – 180.0 kW |
| `TEA` | Evaporator Refrigerant Saturation Temp | Thermodynamic | °F | 30.0 – 60.0 °F |
| `TCA` | Condenser Refrigerant Saturation Temp | Thermodynamic | °F | 70.0 – 115.0 °F |
| `TRE` | Evaporator Temperature Approach | Efficiency | °F | 1.0 – 15.0 °F |
| `TRC` | Condenser Temperature Approach | Efficiency | °F | 2.0 – 20.0 °F |
| `TRC_sub` | Refrigerant Subcooling Temperature | Thermodynamic | °F | 0.0 – 15.0 °F |
| `T_suc` | Compressor Suction Line Temperature | Thermodynamic | °F | 35.0 – 65.0 °F |
| `Tsh_suc` | Compressor Suction Superheat | Control / Health | °F | 2.0 – 25.0 °F |
| `TR_dis` | Compressor Discharge Temperature | Thermal / Mechanical| °F | 90.0 – 180.0 °F |
| `Tsh_dis` | Compressor Discharge Superheat | Control / Health | °F | 10.0 – 50.0 °F |
| `TO_sump` | Compressor Sump Oil Temperature | Mechanical / Lubrication| °F | 80.0 – 150.0 °F |
| `PO_net` | Net Lubricating Oil Pressure | Mechanical / Lubrication| PSI | 15.0 – 120.0 PSI |
| `label` | Multi-class Fault Status Target | System State | Class (1–8) | 1 to 8 |

---

## 2. Derived Performance Metrics

The raw dataset allows direct computation of standard HVAC performance metrics:
1. **Cooling Load ($Q_evap$)**:
   $$\text{Tons} = \frac{\text{Flow (GPM)} \times (\text{TEI} - \text{TEO})}{24}$$
2. **Coefficient of Performance (COP)**:
   $$\text{COP} = \frac{\text{Cooling Capacity (kW)}}{\text{Compressor Power (kW)}}$$
3. **Efficiency (kW/Ton)**:
   $$\text{Efficiency} = \frac{\text{kW}}{\text{Cooling Tons}}$$

---

## 3. Multiclass Target Label Mapping

| Label Index | Fault Description | Physical Manifestation |
| :---: | :--- | :--- |
| **1** | **Normal Operation** | All temperatures, pressures, and approach values within design envelope |
| **2** | **Refrigerant Overcharge** | High discharge pressure, high subcooling (`TRC_sub > 10°F`), elevated power `kW` |
| **3** | **Refrigerant Leak / Undercharge** | Low suction pressure, high suction superheat (`Tsh_suc > 15°F`), reduced COP |
| **4** | **Condenser Fouling** | Elevated condenser approach (`TRC > 10°F`), high condensing temp `TCA` |
| **5** | **Reduced Condenser Flow** | High condenser temperature difference (`TCO - TCI > 15°F`), high discharge temp |
| **6** | **Non-Condensable Gases** | Fluctuating high discharge pressure, elevated discharge superheat |
| **7** | **Excess Oil / Lubrication Issue**| High sump temp (`TO_sump > 140°F`), abnormal net oil pressure `PO_net` |
| **8** | **Reduced Evaporator Flow** | Large evaporator temperature drop (`TEI - TEO > 15°F`), low suction temp |

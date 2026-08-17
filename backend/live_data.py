import pandas as pd
import numpy as np
import json
from pathlib import Path
from collections import deque
from scenarios import apply_scenario

BASE_DIR = Path(__file__).resolve().parent.parent

OPERATIONAL_PATH = BASE_DIR / "data" / "processed" / "transformer_merged.csv"
HEALTH_PATH = BASE_DIR / "data" / "raw" / "Health index1.csv"
FEATURES_V3_PATH = BASE_DIR / "models" / "operational_features_v3.csv"
TRANSFORMERS_CONFIG_PATH = BASE_DIR / "backend" / "transformers.json"

OPERATIONAL_FEATURES_RAW = [
    "ATI", "OTI", "WTI", "OLI",
    "VL1", "VL2", "VL3", "VL12", "VL23", "VL31",
    "IL1", "IL2", "IL3", "INUT",
    "WL1", "WL2", "WL3",
    "VAL1", "VAL2", "VAL3",
    "RVAL1", "RVAL2", "RVAL3",
    "PFL1", "PFL2", "PFL3",
    "Avg_PF", "Sum_PF",
    "FRQ",
    "THDVL1", "THDVL2", "THDVL3",
    "THDIL1", "THDIL2", "THDIL3",
    "KW", "KVA", "KVAR",
    "MPD", "MKVAD"
]

HEALTH_FEATURES = [
    "Hydrogen", "Oxigen", "Nitrogen", "Methane", "CO", "CO2",
    "Ethylene", "Ethane", "Acethylene", "DBDS",
    "Power factor", "Interfacial V", "Dielectric rigidity", "Water content"
]


class FleetReplayEngine:
    def __init__(self):
        self.transformers_config = []
        self.transformers_map = {}
        self.pointers = {}
        self.risk_histories = {}
        
        self.operational_df = None
        self.health_df = None
        self.features_v3_list = []
        self.engineered_df = None

        self._load_config()
        self._load_data()

    def _load_config(self):
        if TRANSFORMERS_CONFIG_PATH.exists():
            with open(TRANSFORMERS_CONFIG_PATH, "r") as f:
                self.transformers_config = json.load(f)
        else:
            self.transformers_config = [
                {
                    "transformer_id": "TX-001",
                    "display_name": "Substation Main TX-1",
                    "location": "Coimbatore",
                    "scenario": "NORMAL",
                    "enabled": True,
                    "description": "Primary regional substation transformer."
                }
            ]

        for tx in self.transformers_config:
            tx_id = tx["transformer_id"]
            self.transformers_map[tx_id] = tx
            self.pointers[tx_id] = 0
            self.risk_histories[tx_id] = deque(maxlen=50)

    def _load_data(self):
        if FEATURES_V3_PATH.exists():
            with open(FEATURES_V3_PATH, "r") as f:
                self.features_v3_list = [line.strip() for line in f if line.strip()]

        if OPERATIONAL_PATH.exists():
            df = pd.read_csv(OPERATIONAL_PATH)
            df["DeviceTimeStamp"] = pd.to_datetime(df["DeviceTimeStamp"], errors="coerce")
            df = df.dropna(subset=["DeviceTimeStamp"]).sort_values("DeviceTimeStamp").reset_index(drop=True)
            
            for col in OPERATIONAL_FEATURES_RAW:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
                else:
                    df[col] = 0.0
                    
            self.operational_df = df
            self._compute_temporal_features()
        else:
            self.operational_df = pd.DataFrame()
            self.engineered_df = pd.DataFrame()

        if HEALTH_PATH.exists():
            h_df = pd.read_csv(HEALTH_PATH)
            for col in HEALTH_FEATURES:
                if col in h_df.columns:
                    h_df[col] = pd.to_numeric(h_df[col], errors="coerce").fillna(0.0)
                else:
                    h_df[col] = 0.0
            self.health_df = h_df
        else:
            self.health_df = pd.DataFrame()

    def _compute_temporal_features(self):
        df = self.operational_df
        df_time = df.set_index("DeviceTimeStamp")
        
        eng_cols = {}
        for col in OPERATIONAL_FEATURES_RAW:
            eng_cols[col] = df[col].values

        KEY_VARS = ["OTI", "WTI", "ATI", "OLI", "VL1", "IL1", "KW", "KVA", "Avg_PF", "THDVL1", "THDIL1", "MPD"]
        for col in KEY_VARS:
            r30 = df_time[col].rolling("30min")
            eng_cols[f"{col}_roll30m_mean"] = r30.mean().values
            eng_cols[f"{col}_roll30m_std"] = r30.std().fillna(0.0).values
            
            r60 = df_time[col].rolling("60min")
            eng_cols[f"{col}_roll60m_mean"] = r60.mean().values
            eng_cols[f"{col}_roll60m_max"] = r60.max().values
            
            eng_cols[f"{col}_diff1"] = df[col].diff(1).fillna(0.0).values

        eng_df = pd.DataFrame(eng_cols).fillna(0.0)
        self.engineered_df = eng_df

    def get_transformers(self):
        return self.transformers_config

    def get_transformer_sample(self, tx_id="TX-001"):
        if len(self.operational_df) == 0:
            return {"success": False, "error": "No operational dataset loaded"}

        if tx_id not in self.transformers_map:
            tx_id = "TX-001"

        tx_config = self.transformers_map[tx_id]
        ptr = self.pointers[tx_id]
        idx = ptr % len(self.operational_df)
        op_row = self.operational_df.iloc[idx]

        # Raw features
        op_data_raw = {f: float(op_row[f]) for f in OPERATIONAL_FEATURES_RAW}

        # V3 Engineered features
        op_data_v3 = {}
        if len(self.engineered_df) > idx:
            eng_row = self.engineered_df.iloc[idx]
            for feature in self.features_v3_list:
                if feature in eng_row:
                    op_data_v3[feature] = float(eng_row[feature])
                else:
                    op_data_v3[feature] = float(op_data_raw.get(feature, 0.0))

        # Health DGA data
        health_data = {}
        if len(self.health_df) > 0:
            h_row = self.health_df.iloc[ptr % len(self.health_df)]
            for feature in HEALTH_FEATURES:
                health_data[feature] = float(h_row[feature])

        # Dummy climate dictionary for scenario transformation
        base_climate = {"temperature": 28.5, "humidity": 65.0, "rain": 0.0, "wind": 12.0, "climate_stress": 19.7}

        # Apply deterministic scenario stream variation if configured
        scenario_name = tx_config.get("scenario", "NORMAL")
        mod_raw, mod_v3, mod_health, mod_climate, deltas, meta = apply_scenario(
            scenario_name, op_data_raw, op_data_v3, health_data, base_climate
        )

        timestamp_str = str(op_row["DeviceTimeStamp"])
        total_samples = len(self.operational_df)
        progress = round(((idx + 1) / total_samples) * 100, 2)

        # Advance pointer for this specific transformer
        self.pointers[tx_id] = (ptr + 1) % total_samples

        return {
            "success": True,
            "source": "historical_replay",
            "transformer_id": tx_id,
            "display_name": tx_config["display_name"],
            "location": tx_config["location"],
            "scenario": meta,
            "timestamp": timestamp_str,
            "sample_number": ptr + 1,
            "current_index": idx + 1,
            "total_samples": total_samples,
            "progress_percent": progress,
            "data": mod_raw,
            "data_v3": mod_v3,
            "health_data": mod_health,
            "scenario_impact": deltas
        }

    def get_fleet_samples(self):
        fleet_samples = {}
        for tx in self.transformers_config:
            if tx.get("enabled", True):
                tx_id = tx["transformer_id"]
                fleet_samples[tx_id] = self.get_transformer_sample(tx_id)
        return fleet_samples

    def push_risk_history(self, tx_id, record):
        if tx_id not in self.risk_histories:
            self.risk_histories[tx_id] = deque(maxlen=50)
        self.risk_histories[tx_id].append(record)

    def get_risk_history(self, tx_id="TX-001"):
        if tx_id not in self.risk_histories:
            return []
        return list(self.risk_histories[tx_id])

    def get_fleet_history(self):
        history_map = {}
        for tx_id, deq in self.risk_histories.items():
            history_map[tx_id] = list(deq)
        return history_map

    def reset_fleet(self):
        for tx_id in self.pointers:
            self.pointers[tx_id] = 0
            self.risk_histories[tx_id].clear()
        return {
            "success": True,
            "message": "All virtual transformer replay streams reset successfully"
        }

    def get_status(self, tx_id="TX-001"):
        if len(self.operational_df) == 0:
            return {"success": False, "error": "No operational dataset loaded"}

        ptr = self.pointers.get(tx_id, 0)
        idx = ptr % len(self.operational_df)
        op_row = self.operational_df.iloc[idx]
        return {
            "success": True,
            "source": "historical_replay",
            "transformer_id": tx_id,
            "current_index": idx + 1,
            "total_samples": len(self.operational_df),
            "timestamp": str(op_row["DeviceTimeStamp"]),
            "progress_percent": round(((idx + 1) / len(self.operational_df)) * 100, 2)
        }


# Global Singleton Instance
fleet_engine = FleetReplayEngine()


# Single-transformer backwards compatibility helpers
def get_live_data(tx_id="TX-001"):
    return fleet_engine.get_transformer_sample(tx_id)


def reset_replay():
    return fleet_engine.reset_fleet()


def get_replay_status(tx_id="TX-001"):
    return fleet_engine.get_status(tx_id)


def push_risk_history(record, tx_id="TX-001"):
    fleet_engine.push_risk_history(tx_id, record)


def get_risk_history(tx_id="TX-001"):
    return fleet_engine.get_risk_history(tx_id)


# Multi-transformer Fleet Helpers
def get_transformers():
    return fleet_engine.get_transformers()


def get_fleet_samples():
    return fleet_engine.get_fleet_samples()


def reset_fleet():
    return fleet_engine.reset_fleet()


def push_fleet_history(tx_id, record):
    fleet_engine.push_risk_history(tx_id, record)


def get_fleet_history():
    return fleet_engine.get_fleet_history()
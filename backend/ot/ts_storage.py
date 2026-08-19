"""
backend/ot/ts_storage.py
========================
SQLite-based time-series storage engine for CascadeGuard IoT telemetry.
Handles insertion, indexing, and history querying of sensor values.
"""
import sqlite3
import threading
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "data" / "telemetry_timeseries.db"

# Thread safety lock
db_lock = threading.Lock()

def init_db():
    """Initializes the database schema and indexes."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with db_lock:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                device_id TEXT NOT NULL,
                asset_id TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                measurement TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                quality TEXT NOT NULL,
                source TEXT NOT NULL
            );
        """)
        # Indexes for fast historical queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_device_time ON telemetry_records (device_id, timestamp DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_device_meas_time ON telemetry_records (device_id, measurement, timestamp DESC);")
        conn.commit()
        conn.close()

def insert_telemetry_point(
    timestamp: str, device_id: str, asset_id: str, asset_type: str,
    measurement: str, value: float, unit: str, quality: str, source: str
):
    """Inserts a single normalized measurement point into the database."""
    with db_lock:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO telemetry_records (timestamp, device_id, asset_id, asset_type, measurement, value, unit, quality, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, device_id, asset_id, asset_type, measurement, float(value), unit, quality, source))
        conn.commit()
        conn.close()

def get_latest_points(device_id: str) -> dict:
    """Returns a dictionary of latest measurements for a device."""
    with db_lock:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.measurement, r.value, r.timestamp, r.unit, r.quality, r.source
            FROM telemetry_records r
            INNER JOIN (
                SELECT measurement, MAX(timestamp) as max_t
                FROM telemetry_records
                WHERE device_id = ?
                GROUP BY measurement
            ) group_max ON r.measurement = group_max.measurement AND r.timestamp = group_max.max_t
            WHERE r.device_id = ?
        """, (device_id, device_id))
        rows = cursor.fetchall()
        conn.close()
    
    return {row["measurement"]: {
        "value": row["value"],
        "timestamp": row["timestamp"],
        "unit": row["unit"],
        "quality": row["quality"],
        "source": row["source"]
    } for row in rows}

def get_historical_series(device_id: str, measurement: str, limit: int = 100) -> list:
    """Returns historical list of points for a device and measurement."""
    with db_lock:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, value, unit, quality, source
            FROM telemetry_records
            WHERE device_id = ? AND measurement = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (device_id, measurement, limit))
        rows = cursor.fetchall()
        conn.close()
        
    return [{
        "timestamp": r["timestamp"],
        "value": r["value"],
        "unit": r["unit"],
        "quality": r["quality"],
        "source": r["source"]
    } for r in reversed(rows)]

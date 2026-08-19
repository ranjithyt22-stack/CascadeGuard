"""
CascadeGuard AI — Multi-Site Infrastructure Registry
Phase 14: Multi-Site Regional Command Center & Phase 1 Foundation

Manages registered industrial facilities, exact geographic coordinates, asset mappings, and site operational statuses.
Persists site registry data to disk so user-created facilities remain across restarts.
"""

import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REGISTRY_FILE_PATH = DATA_DIR / "sites_registry.json"

DEMO_SITES = [
    {
        "site_id": "CBE-001",
        "site_name": "Coimbatore Industrial Facility",
        "city": "Coimbatore",
        "latitude": 11.00555,
        "longitude": 76.96612,
        "transformer_id": "TX-001",
        "chiller_id": "CH-001",
        "water_pump_id": "WP-001",
        "asset_ids": {"transformer": "TX-001", "chiller": "CH-001", "water_pump": "WP-001"},
        "timezone": "Asia/Kolkata",
        "status": "ACTIVE",
        "telemetry_mode": "MOCK"
    },
    {
        "site_id": "CHN-001",
        "site_name": "Chennai Regional Hub",
        "city": "Chennai",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "transformer_id": "TR-001",
        "chiller_id": "CH-001",
        "water_pump_id": "WP-001",
        "asset_ids": {"transformer": "TR-001", "chiller": "CH-001", "water_pump": "WP-001"},
        "timezone": "Asia/Kolkata",
        "status": "ACTIVE",
        "telemetry_mode": "MOCK"
    },
    {
        "site_id": "MDU-001",
        "site_name": "Madurai Industrial Site",
        "city": "Madurai",
        "latitude": 9.9252,
        "longitude": 78.1198,
        "transformer_id": "TR-002",
        "chiller_id": "CH-002",
        "water_pump_id": "WP-002",
        "asset_ids": {"transformer": "TR-002", "chiller": "CH-002", "water_pump": "WP-002"},
        "timezone": "Asia/Kolkata",
        "status": "ACTIVE",
        "telemetry_mode": "MOCK"
    },
    {
        "site_id": "TRY-001",
        "site_name": "Trichy Logistics Center",
        "city": "Trichy",
        "latitude": 10.7905,
        "longitude": 78.7047,
        "transformer_id": "TR-003",
        "chiller_id": "CH-003",
        "water_pump_id": "WP-003",
        "asset_ids": {"transformer": "TR-003", "chiller": "CH-003", "water_pump": "WP-003"},
        "timezone": "Asia/Kolkata",
        "status": "ACTIVE",
        "telemetry_mode": "MOCK"
    },
    {
        "site_id": "SLM-001",
        "site_name": "Salem Substation Plant",
        "city": "Salem",
        "latitude": 11.6643,
        "longitude": 78.1460,
        "transformer_id": "TR-004",
        "chiller_id": "CH-004",
        "water_pump_id": "WP-004",
        "asset_ids": {"transformer": "TR-004", "chiller": "CH-004", "water_pump": "WP-004"},
        "timezone": "Asia/Kolkata",
        "status": "ACTIVE",
        "telemetry_mode": "MOCK"
    }
]


def validate_coordinates(latitude, longitude):
    if latitude is None or latitude == "":
        return False, "Latitude is required."
    if longitude is None or longitude == "":
        return False, "Longitude is required."
    try:
        lat = float(latitude)
    except (ValueError, TypeError):
        return False, "Latitude must be numeric."
    try:
        lon = float(longitude)
    except (ValueError, TypeError):
        return False, "Longitude must be numeric."

    if not (-90.0 <= lat <= 90.0):
        return False, "Latitude must be between -90 and 90."
    if not (-180.0 <= lon <= 180.0):
        return False, "Longitude must be between -180 and 180."
    return True, None


def normalize_site_dict(site):
    """Ensures consistent top-level and asset_ids representation."""
    s = dict(site)
    tx_id = s.get("transformer_id") or s.get("asset_ids", {}).get("transformer") or "TR-001"
    ch_id = s.get("chiller_id") or s.get("asset_ids", {}).get("chiller") or "CH-001"
    wp_id = s.get("water_pump_id") or s.get("asset_ids", {}).get("water_pump") or "WP-001"

    s["transformer_id"] = str(tx_id).strip()
    s["chiller_id"] = str(ch_id).strip()
    s["water_pump_id"] = str(wp_id).strip()
    s["asset_ids"] = {
        "transformer": s["transformer_id"],
        "chiller": s["chiller_id"],
        "water_pump": s["water_pump_id"]
    }
    s["site_id"] = str(s.get("site_id", "")).strip()
    s["site_name"] = str(s.get("site_name", "")).strip()
    s["city"] = str(s.get("city", "Unknown")).strip()
    s["latitude"] = float(s.get("latitude", 0.0))
    s["longitude"] = float(s.get("longitude", 0.0))
    s["timezone"] = s.get("timezone", "Asia/Kolkata")
    s["status"] = s.get("status", "ACTIVE")
    s["telemetry_mode"] = s.get("telemetry_mode", "MOCK")
    return s


class SiteRegistry:
    def __init__(self):
        self.sites = {}
        self.load_sites()

    def _save_sites(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(REGISTRY_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(list(self.sites.values()), f, indent=2)
        except Exception as e:
            print(f"Error persisting site registry to {REGISTRY_FILE_PATH}: {e}")

    def load_sites(self):
        loaded_sites = {}
        if REGISTRY_FILE_PATH.exists():
            try:
                with open(REGISTRY_FILE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for s in data:
                            if isinstance(s, dict) and s.get("site_id"):
                                norm = normalize_site_dict(s)
                                loaded_sites[norm["site_id"]] = norm
            except Exception as e:
                print(f"Error reading site registry from {REGISTRY_FILE_PATH}: {e}")

        # Seed missing demo sites while preserving user-created facilities
        for demo in DEMO_SITES:
            sid = demo["site_id"]
            if sid not in loaded_sites:
                loaded_sites[sid] = normalize_site_dict(demo)

        self.sites = loaded_sites
        self._save_sites()

    def get_all_sites(self, active_only=False):
        if active_only:
            return [dict(s) for s in self.sites.values() if s.get("status") == "ACTIVE"]
        return [dict(s) for s in self.sites.values()]

    def get_site(self, site_id):
        if not site_id:
            return None
        sid = str(site_id).strip()
        if sid in self.sites:
            return dict(self.sites[sid])
        alias_map = {
            "SITE-001": "CBE-001", "CBE-001": "CBE-001",
            "SITE-002": "CHN-001", "CHN-001": "CHN-001",
            "SITE-003": "MDU-001", "MDU-001": "MDU-001",
            "SITE-004": "TRY-001", "TRY-001": "TRY-001",
            "SITE-005": "SLM-001", "SLM-001": "SLM-001"
        }
        mapped_id = alias_map.get(sid)
        if mapped_id and mapped_id in self.sites:
            res = dict(self.sites[mapped_id])
            res["site_id"] = sid
            return res
        return None

    def add_site(self, site_data):
        if not isinstance(site_data, dict):
            return False, "Invalid payload format.", None

        site_id = str(site_data.get("site_id", "")).strip()
        if not site_id:
            return False, "Site ID is required.", None
        if site_id in self.sites:
            return False, f"A facility with this Site ID already exists.", None

        site_name = str(site_data.get("site_name", "")).strip()
        if not site_name:
            return False, "Site Name is required.", None

        city = str(site_data.get("city", "")).strip()
        if not city:
            return False, "City is required.", None

        lat = site_data.get("latitude")
        lon = site_data.get("longitude")
        is_valid, err = validate_coordinates(lat, lon)
        if not is_valid:
            return False, err, None

        tx_id = str(site_data.get("transformer_id", "")).strip()
        ch_id = str(site_data.get("chiller_id", "")).strip()
        wp_id = str(site_data.get("water_pump_id", "")).strip()

        if not tx_id:
            return False, "Transformer ID is required.", None
        if not ch_id:
            return False, "Chiller ID is required.", None
        if not wp_id:
            return False, "Water Pump ID is required.", None

        new_site = normalize_site_dict({
            "site_id": site_id,
            "site_name": site_name,
            "city": city,
            "latitude": float(lat),
            "longitude": float(lon),
            "transformer_id": tx_id,
            "chiller_id": ch_id,
            "water_pump_id": wp_id,
            "timezone": site_data.get("timezone", "Asia/Kolkata"),
            "status": site_data.get("status", "ACTIVE"),
            "telemetry_mode": site_data.get("telemetry_mode", "MOCK")
        })

        self.sites[site_id] = new_site
        self._save_sites()
        return True, f"Facility '{site_id}' created successfully.", new_site

    def update_site(self, site_id, update_data):
        site_id = str(site_id).strip()
        if site_id not in self.sites:
            return False, f"Site ID '{site_id}' not found.", None

        site = self.sites[site_id]

        if "site_name" in update_data:
            s_name = str(update_data["site_name"]).strip()
            if not s_name:
                return False, "Site Name is required.", None
            site["site_name"] = s_name

        if "city" in update_data:
            c_val = str(update_data["city"]).strip()
            if not c_val:
                return False, "City is required.", None
            site["city"] = c_val

        lat = update_data.get("latitude", site["latitude"])
        lon = update_data.get("longitude", site["longitude"])
        is_valid, err = validate_coordinates(lat, lon)
        if not is_valid:
            return False, err, None

        site["latitude"] = float(lat)
        site["longitude"] = float(lon)

        if "transformer_id" in update_data:
            tx = str(update_data["transformer_id"]).strip()
            if not tx:
                return False, "Transformer ID is required.", None
            site["transformer_id"] = tx
        if "chiller_id" in update_data:
            ch = str(update_data["chiller_id"]).strip()
            if not ch:
                return False, "Chiller ID is required.", None
            site["chiller_id"] = ch
        if "water_pump_id" in update_data:
            wp = str(update_data["water_pump_id"]).strip()
            if not wp:
                return False, "Water Pump ID is required.", None
            site["water_pump_id"] = wp

        if "status" in update_data:
            site["status"] = update_data["status"]
        if "telemetry_mode" in update_data:
            site["telemetry_mode"] = update_data["telemetry_mode"]

        norm_updated = normalize_site_dict(site)
        self.sites[site_id] = norm_updated
        self._save_sites()
        return True, f"Facility '{site_id}' updated successfully.", dict(norm_updated)

    def delete_site(self, site_id):
        site_id = str(site_id).strip()
        if site_id not in self.sites:
            return False, f"Site ID '{site_id}' not found."
        del self.sites[site_id]
        self._save_sites()
        return True, f"Facility '{site_id}' deleted successfully."

    def activate_site(self, site_id):
        site_id = str(site_id).strip()
        if site_id not in self.sites:
            return False, f"Site ID '{site_id}' not found."
        self.sites[site_id]["status"] = "ACTIVE"
        self._save_sites()
        return True, f"Site '{site_id}' activated."

    def deactivate_site(self, site_id):
        site_id = str(site_id).strip()
        if site_id not in self.sites:
            return False, f"Site ID '{site_id}' not found."
        self.sites[site_id]["status"] = "INACTIVE"
        self._save_sites()
        return True, f"Site '{site_id}' deactivated."


"""
CascadeGuard AI — Multi-Site Infrastructure Registry
Phase 14: Multi-Site Regional Command Center

Manages registered industrial facilities, exact geographic coordinates, asset mappings, and site operational statuses.
"""

INITIAL_SITES = [
    {
        "site_id": "SITE-001",
        "site_name": "Coimbatore Industrial Facility",
        "city": "Coimbatore",
        "latitude": 11.00555,
        "longitude": 76.96612,
        "timezone": "Asia/Kolkata",
        "status": "ACTIVE",
        "asset_ids": {
            "transformer": "TX-001",
            "chiller": "CH-001",
            "water_pump": "WP-001"
        },
        "telemetry_mode": "MOCK"
    },
    {
        "site_id": "SITE-002",
        "site_name": "Chennai Industrial Facility",
        "city": "Chennai",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "timezone": "Asia/Kolkata",
        "status": "ACTIVE",
        "asset_ids": {
            "transformer": "TX-002",
            "chiller": "CH-002",
            "water_pump": "WP-002"
        },
        "telemetry_mode": "MOCK"
    },
    {
        "site_id": "SITE-003",
        "site_name": "Bengaluru Industrial Facility",
        "city": "Bengaluru",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "timezone": "Asia/Kolkata",
        "status": "ACTIVE",
        "asset_ids": {
            "transformer": "TX-003",
            "chiller": "CH-003",
            "water_pump": "WP-003"
        },
        "telemetry_mode": "MOCK"
    },
    {
        "site_id": "SITE-004",
        "site_name": "Madurai Industrial Facility",
        "city": "Madurai",
        "latitude": 9.9252,
        "longitude": 78.1198,
        "timezone": "Asia/Kolkata",
        "status": "ACTIVE",
        "asset_ids": {
            "transformer": "TX-004",
            "chiller": "CH-004",
            "water_pump": "WP-004"
        },
        "telemetry_mode": "MOCK"
    },
    {
        "site_id": "SITE-005",
        "site_name": "Salem Industrial Facility",
        "city": "Salem",
        "latitude": 11.6643,
        "longitude": 78.1460,
        "timezone": "Asia/Kolkata",
        "status": "ACTIVE",
        "asset_ids": {
            "transformer": "TX-005",
            "chiller": "CH-005",
            "water_pump": "WP-005"
        },
        "telemetry_mode": "MOCK"
    }
]


def validate_coordinates(latitude, longitude):
    try:
        lat = float(latitude)
        lon = float(longitude)
        if not (-90.0 <= lat <= 90.0):
            return False, f"Latitude {lat} out of bounds [-90.0, 90.0]"
        if not (-180.0 <= lon <= 180.0):
            return False, f"Longitude {lon} out of bounds [-180.0, 180.0]"
        return True, None
    except (ValueError, TypeError):
        return False, "Latitude and longitude must be valid numerical floats."


class SiteRegistry:
    def __init__(self):
        self.sites = {}
        for s in INITIAL_SITES:
            self.sites[s["site_id"]] = dict(s)

    def get_all_sites(self, active_only=False):
        if active_only:
            return [dict(s) for s in self.sites.values() if s.get("status") == "ACTIVE"]
        return [dict(s) for s in self.sites.values()]

    def get_site(self, site_id):
        s = self.sites.get(site_id)
        return dict(s) if s else None

    def add_site(self, site_data):
        site_id = site_data.get("site_id")
        if not site_id:
            return False, "Missing required field: site_id", None
        if site_id in self.sites:
            return False, f"Site ID '{site_id}' already exists.", None

        site_name = site_data.get("site_name") or site_data.get("name")
        if not site_name:
            return False, "Missing required field: site_name", None

        city = site_data.get("city") or site_data.get("location") or "Unknown"
        lat = site_data.get("latitude")
        lon = site_data.get("longitude")

        is_valid, err = validate_coordinates(lat, lon)
        if not is_valid:
            return False, err, None

        new_site = {
            "site_id": str(site_id).strip(),
            "site_name": str(site_name).strip(),
            "city": str(city).strip(),
            "latitude": float(lat),
            "longitude": float(lon),
            "timezone": site_data.get("timezone", "Asia/Kolkata"),
            "status": site_data.get("status", "ACTIVE"),
            "asset_ids": site_data.get("asset_ids", {
                "transformer": f"TX-{site_id}",
                "chiller": f"CH-{site_id}",
                "water_pump": f"WP-{site_id}"
            }),
            "telemetry_mode": site_data.get("telemetry_mode", "MOCK")
        }

        self.sites[site_id] = new_site
        return True, f"Site '{site_id}' created successfully.", new_site

    def update_site(self, site_id, update_data):
        if site_id not in self.sites:
            return False, f"Site ID '{site_id}' not found.", None

        site = self.sites[site_id]
        if "latitude" in update_data or "longitude" in update_data:
            lat = update_data.get("latitude", site["latitude"])
            lon = update_data.get("longitude", site["longitude"])
            is_valid, err = validate_coordinates(lat, lon)
            if not is_valid:
                return False, err, None
            site["latitude"] = float(lat)
            site["longitude"] = float(lon)

        if "site_name" in update_data:
            site["site_name"] = str(update_data["site_name"]).strip()
        if "city" in update_data:
            site["city"] = str(update_data["city"]).strip()
        if "status" in update_data:
            site["status"] = update_data["status"]
        if "asset_ids" in update_data and isinstance(update_data["asset_ids"], dict):
            site["asset_ids"].update(update_data["asset_ids"])
        if "telemetry_mode" in update_data:
            site["telemetry_mode"] = update_data["telemetry_mode"]

        return True, f"Site '{site_id}' updated successfully.", dict(site)

    def delete_site(self, site_id):
        if site_id not in self.sites:
            return False, f"Site ID '{site_id}' not found."
        del self.sites[site_id]
        return True, f"Site '{site_id}' deleted successfully."

    def activate_site(self, site_id):
        if site_id not in self.sites:
            return False, f"Site ID '{site_id}' not found."
        self.sites[site_id]["status"] = "ACTIVE"
        return True, f"Site '{site_id}' activated."

    def deactivate_site(self, site_id):
        if site_id not in self.sites:
            return False, f"Site ID '{site_id}' not found."
        self.sites[site_id]["status"] = "INACTIVE"
        return True, f"Site '{site_id}' deactivated."

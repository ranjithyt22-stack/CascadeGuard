import sys
from pathlib import Path
import traceback

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app import app

client = app.test_client()

print("--- TESTING /api/fleet-status ---")
r1 = client.get("/api/fleet-status")
print("Status:", r1.status_code)
if r1.status_code != 200:
    print("Error output:", r1.data.decode())
else:
    print("Success:", list(r1.get_json().keys()))

print("\n--- TESTING /api/multi-asset-analyze ---")
r2 = client.get("/api/multi-asset-analyze?location=Coimbatore&tx_id=TX-001")
print("Status:", r2.status_code)
if r2.status_code != 200:
    print("Error output:", r2.data.decode())
else:
    print("Success:", list(r2.get_json().keys()))

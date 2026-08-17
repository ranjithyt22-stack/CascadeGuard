import requests
import json

BASE_URL = "http://127.0.0.1:5050"

res = requests.get(f"{BASE_URL}/api/realtime-analyze?location=Coimbatore&tx_id=TX-001")
print("STATUS CODE:", res.status_code)
try:
    data = res.json()
    print("KEYS:", list(data.keys()))
    if not data.get("success"):
        print("ERROR:", data.get("error"))
    else:
        print("ASSETS:", list(data.get("assets", {}).keys()))
        print("TX ASSET:", data.get("assets", {}).get("transformer"))
except Exception as e:
    print("TEXT:", res.text)

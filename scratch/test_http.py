import requests

try:
    print("Testing HTTP GET http://127.0.0.1:5000/api/fleet-status ...")
    r = requests.get("http://127.0.0.1:5000/api/fleet-status", timeout=5)
    print("STATUS:", r.status_code)
    print("HEADERS:", r.headers)
    print("TEXT SNIPPET:", repr(r.text[:200]))
except Exception as e:
    import traceback
    traceback.print_exc()

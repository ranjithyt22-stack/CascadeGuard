import json

def inspect_json(filepath):
    print(f"--- JSON: {filepath} ---")
    with open(filepath, 'r') as f:
        data = json.load(f)
    if isinstance(data, list):
        print(f"Type: List, Count: {len(data)}")
        if len(data) > 0:
            print("First item keys:", data[0].keys())
            print("Sample item:", data[0])
    elif isinstance(data, dict):
        print(f"Type: Dict, Keys: {list(data.keys())}")
        for k in list(data.keys())[:3]:
            print(f"Key '{k}' sample:", data[k])

if __name__ == "__main__":
    inspect_json("data/incidents_db.json")
    inspect_json("data/model_registry.json")
    inspect_json("data/sites_registry.json")

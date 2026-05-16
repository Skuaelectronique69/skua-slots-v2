from pathlib import Path
import json

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "data" / "runtime_registry.json"

def load_runtime_registry():
    if not REGISTRY_PATH.exists():
        return {
            "status": "missing",
            "registry": {}
        }

    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    return {
        "status": "ok",
        "registry": data
    }

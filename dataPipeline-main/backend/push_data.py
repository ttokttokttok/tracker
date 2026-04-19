"""Push all seed data to Butterbase."""
import json
import os
import sys
from pathlib import Path

import requests

SK = os.getenv("BUTTERBASE_SERVICE_KEY")
APP = os.getenv("BUTTERBASE_APP_ID")
RUN_ID = os.getenv("BUTTERBASE_RUN_ID")

if not SK or not APP or not RUN_ID:
    print("ERROR: Set BUTTERBASE_SERVICE_KEY, BUTTERBASE_APP_ID, and BUTTERBASE_RUN_ID.")
    sys.exit(1)

BASE = f"https://api.butterbase.ai/v1/{APP}"
HEADERS = {"Authorization": f"Bearer {SK}", "Content-Type": "application/json"}

seed_path = Path(os.getenv("SEED_DATA_PATH", Path(__file__).parent.parent / "pipeline" / "output" / "seed_data.json"))
if not seed_path.exists():
    print(f"ERROR: Seed data file not found: {seed_path}")
    sys.exit(1)

SEED = json.loads(seed_path.read_text())

def post(table, data):
    # Butterbase needs JSONB fields sent as stringified JSON
    payload = {}
    for k, v in data.items():
        if isinstance(v, (list, dict)):
            payload[k] = json.dumps(v)
        else:
            payload[k] = v
    r = requests.post(f"{BASE}/{table}", headers=HEADERS, json=payload)
    resp = r.json()
    if "error" in resp:
        print(f"  ERROR on {table}: {resp['error']}")
        return None
    print(f"  {table}: {resp.get('id', 'ok')}")
    return resp.get("id")

# Pipeline
print("=== Pipeline ===")
p = SEED["pipeline"]
PIPE_ID = post("pipelines", {
    "run_id": RUN_ID,
    "label": p["label"],
    "status": p["status"],
    "video_url": p["source_video"]["url"],
    "video_filename": p["source_video"]["filename"],
    "duration_ms": p["source_video"]["duration_ms"],
    "video_width": p["source_video"]["width"],
    "video_height": p["source_video"]["height"],
    "detected_objects": p["detected_objects"],
    "stage_status": p["stage_status"],
})

# Tracks
print("\n=== Tracks ===")
for t in SEED["tracks"]:
    post("tracks", {
        "pipeline_id": PIPE_ID,
        "label": t["label"],
        "track_type": t["type"],
        "color": t["color"],
        "frames": t["frames"],
    })

# World Model
print("\n=== World Model ===")
wm = SEED["worldModel"]
post("world_models", {
    "pipeline_id": PIPE_ID,
    "target_object": wm["target_object"],
    "action_label": wm["action_label"],
    "duration_ms": wm["duration_ms"],
    "objects": wm["objects"],
    "actions": wm["actions"],
    "relations": wm["relations"],
})

# Synthetic Outputs
print("\n=== Synthetic Outputs ===")
for s in SEED["syntheticOutputs"]:
    post("synthetic_outputs", {
        "pipeline_id": PIPE_ID,
        "run_id": RUN_ID,
        "label": s["label"],
        "status": s["status"],
        "provider": s.get("provider", ""),
        "prompt": s["prompt"],
        "constraints": s["constraints"],
        "video_url": s.get("video_url", ""),
    })

# Verify
print("\n=== Verify ===")
for table in ["runs", "pipelines", "tracks", "world_models", "synthetic_outputs"]:
    r = requests.get(f"{BASE}/{table}", headers=HEADERS)
    data = r.json()
    count = len(data) if isinstance(data, list) else data.get("count", "?")
    print(f"  {table}: {count} rows")

print("\nDone!")

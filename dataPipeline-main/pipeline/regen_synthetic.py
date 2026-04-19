"""
Regenerate synthetic videos with prompts that match the source video camera angle.
Source video is a close-up stationary front view — synthetic prompts must match.
"""

import os, sys, json, time, shutil, requests
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

from byteplussdkarkruntime import Ark

client = Ark(
    base_url="https://ark.ap-southeast.bytepluses.com/api/v3",
    api_key=os.getenv("ARK_API_KEY"),
)

OUTPUT_DIR = Path(__file__).parent / "output"
MEDIA_DIR = Path(__file__).parent.parent / "dashboard" / "public" / "media"
MODEL = "seedance-1-5-pro-251215"

# Prompts match source video angle: close-up, stationary front camera, table surface visible
VARIATIONS = [
    {
        "id": "warehouse",
        "label": "Warehouse",
        "prompt": (
            "Close-up stationary front camera view of a human right hand reaching for "
            "a metallic soda can sitting on a metal workbench. The hand grasps the can, "
            "lifts it, moves it to the left side of the bench, and places it down. "
            "Industrial warehouse background with concrete floor and metal shelving. "
            "Overhead fluorescent lighting. Camera does not move."
        ),
    },
    {
        "id": "kitchen",
        "label": "Kitchen Counter",
        "prompt": (
            "Close-up stationary front camera view of a human right hand reaching for "
            "a soda can on a marble kitchen countertop. The hand grasps the can, lifts it, "
            "moves it to the left, and sets it back down on the counter. Modern kitchen with "
            "warm interior lighting and appliances in background. Camera does not move."
        ),
    },
    {
        "id": "outdoor",
        "label": "Outdoor Picnic",
        "prompt": (
            "Close-up stationary front camera view of a human right hand reaching for "
            "a soda can on a wooden picnic table. The hand grasps the can, lifts it, "
            "moves it to the left, and places it back down. Outdoor park setting with "
            "natural daylight, grass and trees in background. Camera does not move."
        ),
    },
]

def download_video(url, dest):
    print(f"  Downloading {dest.name}...")
    r = requests.get(url, stream=True, timeout=120)
    r.raise_for_status()
    with open(dest, 'wb') as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)
    print(f"  {dest.stat().st_size / 1024:.0f} KB")

def main():
    print("=== Regenerating Synthetic Videos (angle-matched) ===\n")

    jobs = []
    for v in VARIATIONS:
        print(f"Submitting: {v['label']}")
        r = client.content_generation.tasks.create(
            model=MODEL,
            content=[{"type": "text", "text": v["prompt"]}],
            generate_audio=False, ratio="16:9", duration=5, watermark=False,
        )
        print(f"  Task: {r.id}")
        jobs.append({"task_id": r.id, "var": v})

    print("\nPolling...")
    results = {}
    pending = list(jobs)
    for attempt in range(40):
        if not pending:
            break
        time.sleep(15)
        still = []
        for j in pending:
            d = client.content_generation.tasks.get(task_id=j["task_id"]).to_dict()
            s = d.get("status", "?")
            if s == "succeeded":
                print(f"  [{attempt+1}] {j['var']['label']}: DONE")
                results[j["var"]["id"]] = d.get("content", {}).get("video_url", "")
            elif s == "failed":
                print(f"  [{attempt+1}] {j['var']['label']}: FAILED")
                results[j["var"]["id"]] = ""
            else:
                print(f"  [{attempt+1}] {j['var']['label']}: {s}")
                still.append(j)
        pending = still

    print("\nDownloading...")
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    for v in VARIATIONS:
        url = results.get(v["id"], "")
        if url:
            f = f"synthetic_{v['id']}.mp4"
            dest = OUTPUT_DIR / f
            download_video(url, dest)
            shutil.copy2(dest, MEDIA_DIR / f)

    # Update seed data synthetic entries
    seed_js = Path(__file__).parent.parent / "dashboard" / "src" / "data" / "seedRun.js"
    content = seed_js.read_text(encoding="utf-8", errors="replace")

    now = datetime.now(timezone.utc).isoformat()
    new_outputs = []
    for v in VARIATIONS:
        url = results.get(v["id"], "")
        status = "succeeded" if url else "failed"
        fname = f"synthetic_{v['id']}.mp4" if url else ""
        new_outputs.append({
            "synthetic_id": f"synth_{v['id']}_001",
            "pipeline_id": "pipe_front_001",
            "run_id": "run_can_pickup_001",
            "label": v["label"],
            "status": status,
            "provider": "seedance_1_5_pro",
            "prompt": v["prompt"],
            "constraints": [
                "preserve same target object: can",
                "preserve same action phase order",
                "preserve same camera angle: stationary front view",
                "preserve same task outcome",
            ],
            "video_url": f"/media/{fname}" if fname else "",
            "created_at": now,
        })

    # Replace syntheticOutputs in the JS file
    marker = "export const syntheticOutputs = "
    idx = content.find(marker)
    if idx >= 0:
        end = content.find(";\n", idx)
        if end >= 0:
            replacement = marker + json.dumps(new_outputs, indent=2)
            content = content[:idx] + replacement + content[end:]
            seed_js.write_text(content, encoding="utf-8")
            print(f"\nSeed JS updated")

    succeeded = sum(1 for u in results.values() if u)
    print(f"\nDONE: {succeeded}/{len(VARIATIONS)} videos regenerated with matched angles")

if __name__ == "__main__":
    main()

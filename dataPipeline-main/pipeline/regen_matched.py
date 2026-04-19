"""
Regenerate synthetic videos:
- Match the source video action (hand interacting with / opening a can)
- Use varied interesting camera angles (robot POV style, not identical front view)
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

# Prompts match the SOURCE video content (hand reaching for and opening a can)
# with varied interesting camera angles
VARIATIONS = [
    {
        "id": "warehouse",
        "label": "Warehouse",
        "prompt": (
            "A human hand reaches toward a soda can sitting on a metal workbench and "
            "opens it with a pulling motion on the tab. The can stays on the surface. "
            "Industrial warehouse setting with concrete floor and metal shelving in background. "
            "Camera is angled from slightly above and to the right, looking down at the table, "
            "like a robot arm's perspective. Overhead fluorescent lighting."
        ),
    },
    {
        "id": "kitchen",
        "label": "Kitchen Counter",
        "prompt": (
            "A human hand reaches toward a soda can on a marble kitchen counter and "
            "opens it by pulling the tab. The can remains on the counter. "
            "Modern kitchen with warm lighting and appliances visible. "
            "Camera is angled from the side at about 45 degrees, slightly elevated, "
            "like a mounted robot camera observing the task."
        ),
    },
    {
        "id": "outdoor",
        "label": "Outdoor Picnic",
        "prompt": (
            "A human hand reaches toward a soda can on a wooden picnic table and "
            "opens it by pulling the tab. The can stays on the table. "
            "Outdoor park setting with natural daylight, grass and trees in background. "
            "Camera is positioned at an angle from above and slightly to the left, "
            "looking down at the table surface, like a robotic observer perspective."
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
    print("=== Regenerating Synthetic Videos (action-matched + varied angles) ===\n")

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

    # Update seed data
    print("\nUpdating seed data...")
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
                "preserve same action: opening the can",
                "preserve varied camera angle: robot POV",
                "preserve same task outcome",
            ],
            "video_url": f"/media/{fname}" if fname else "",
            "created_at": now,
        })

    marker = "export const syntheticOutputs = "
    idx = content.find(marker)
    if idx >= 0:
        end = content.find(";\n", idx)
        if end >= 0:
            replacement = marker + json.dumps(new_outputs, indent=2)
            content = content[:idx] + replacement + content[end:]
            seed_js.write_text(content, encoding="utf-8")
            print("Seed JS updated")

    succeeded = sum(1 for u in results.values() if u)
    print(f"\nDONE: {succeeded}/{len(VARIATIONS)} videos regenerated")


if __name__ == "__main__":
    main()

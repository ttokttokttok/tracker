"""
Resume the pipeline from Step 6 — generate synthetic variations and rebuild seed data.
Uses the source video and real detection data from the first pipeline run.
"""

import os
import sys
import json
import time
import shutil
import requests
import cv2
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

ARK_API_KEY = os.getenv("ARK_API_KEY")
if not ARK_API_KEY:
    print("ERROR: Set ARK_API_KEY in .env")
    sys.exit(1)

from byteplussdkarkruntime import Ark

client = Ark(
    base_url="https://ark.ap-southeast.bytepluses.com/api/v3",
    api_key=ARK_API_KEY,
)

OUTPUT_DIR = Path(__file__).parent / "output"
DASHBOARD_MEDIA_DIR = Path(__file__).parent.parent / "dashboard" / "public" / "media"
SEEDANCE_MODEL = "seedance-1-5-pro-251215"

VARIATIONS = [
    {
        "id": "warehouse",
        "label": "Warehouse",
        "prompt": (
            "A hand picks up a metallic can from a workbench in an industrial warehouse "
            "with concrete floors and metal shelving. The hand reaches from the right side, "
            "grasps the can, lifts it, moves it to the left, and places it down. "
            "Overhead fluorescent lighting, realistic motion."
        ),
    },
    {
        "id": "kitchen",
        "label": "Kitchen Counter",
        "prompt": (
            "A hand picks up an aluminum soda can from a modern kitchen counter with marble surface. "
            "The hand reaches, grasps the can firmly, lifts and moves it to the side, then places it down. "
            "Warm interior lighting, kitchen appliances in background."
        ),
    },
    {
        "id": "outdoor",
        "label": "Outdoor Picnic",
        "prompt": (
            "A hand picks up a soda can from a wooden picnic table outdoors in a park. "
            "The hand reaches, grasps the can, lifts it up, moves it, and places it back down. "
            "Natural daylight, grass and trees in background. Smooth deliberate motion."
        ),
    },
]


def download_video(url, dest_path):
    print(f"  Downloading to {dest_path.name}...")
    r = requests.get(url, stream=True, timeout=120)
    r.raise_for_status()
    with open(dest_path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"  Downloaded {dest_path.stat().st_size / 1024:.0f} KB")


def main():
    print("=" * 60)
    print("  Resume Pipeline — Synthetic Generation + Seed Data")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DASHBOARD_MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    # Submit all jobs at once
    print("\n=== Submitting Seedance Jobs ===")
    jobs = []
    for var in VARIATIONS:
        print(f"  {var['label']}...")
        content = [{"type": "text", "text": var["prompt"]}]

        result = client.content_generation.tasks.create(
            model=SEEDANCE_MODEL,
            content=content,
            generate_audio=False,
            ratio="16:9",
            duration=5,
            watermark=False,
        )
        task_id = result.id
        print(f"    Task ID: {task_id}")
        jobs.append({"task_id": task_id, "variation": var})

    # Poll all jobs
    print("\n=== Polling Jobs ===")
    results = {}
    pending = list(jobs)

    for attempt in range(40):
        if not pending:
            break
        time.sleep(15)
        still_pending = []

        for job in pending:
            task_id = job["task_id"]
            label = job["variation"]["label"]
            result = client.content_generation.tasks.get(task_id=task_id)
            d = result.to_dict()
            status = d.get("status", "unknown")

            if status == "succeeded":
                video_url = d.get("content", {}).get("video_url", "")
                print(f"  [{attempt+1}] {label}: SUCCEEDED")
                results[job["variation"]["id"]] = {"status": "succeeded", "video_url": video_url}
            elif status == "failed":
                print(f"  [{attempt+1}] {label}: FAILED")
                results[job["variation"]["id"]] = {"status": "failed", "video_url": ""}
            else:
                print(f"  [{attempt+1}] {label}: {status}")
                still_pending.append(job)

        pending = still_pending

    for job in pending:
        results[job["variation"]["id"]] = {"status": "failed", "video_url": ""}

    # Download videos
    print("\n=== Downloading Videos ===")
    synthetic_video_files = {}
    for var in VARIATIONS:
        sr = results.get(var["id"], {})
        if sr.get("status") == "succeeded" and sr.get("video_url"):
            filename = f"synthetic_{var['id']}.mp4"
            local_path = OUTPUT_DIR / filename
            download_video(sr["video_url"], local_path)
            shutil.copy2(local_path, DASHBOARD_MEDIA_DIR / filename)
            synthetic_video_files[var["id"]] = filename
            print(f"  Copied to dashboard: {filename}")

    # Rebuild seed data
    print("\n=== Rebuilding Seed Data ===")
    rebuild_seed_data(results, synthetic_video_files)

    succeeded = len([r for r in results.values() if r.get("status") == "succeeded"])
    print(f"\n{'=' * 60}")
    print(f"  DONE — {succeeded}/{len(VARIATIONS)} synthetic videos generated")
    print(f"  Dashboard seed data updated. Restart dev server to see changes.")
    print(f"{'=' * 60}")


def rebuild_seed_data(synthetic_results, synthetic_video_files):
    """Rebuild seedRun.js with real detection data + synthetic videos."""

    source_path = OUTPUT_DIR / "source.mp4"
    cap = cv2.VideoCapture(str(source_path))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_ms = int((total_frames / fps) * 1000) if fps > 0 else 5000
    cap.release()

    now = datetime.now(timezone.utc).isoformat()

    # Real detection data from the pipeline run
    hand_frames = [
        {"t_ms": 0, "bbox": [0, 0, 0, 0], "confidence": 0, "visible": False},
        {"t_ms": 500, "bbox": [407, 0, 593, 516], "confidence": 0.98, "visible": True},
        {"t_ms": 1000, "bbox": [372, 0, 628, 692], "confidence": 0.98, "visible": True},
        {"t_ms": 1500, "bbox": [394, 46, 454, 653], "confidence": 0.98, "visible": True},
        {"t_ms": 2000, "bbox": [398, 1, 602, 698], "confidence": 0.99, "visible": True},
        {"t_ms": 2500, "bbox": [337, 0, 663, 695], "confidence": 0.98, "visible": True},
        {"t_ms": 3000, "bbox": [300, 0, 700, 765], "confidence": 0.97, "visible": True},
        {"t_ms": 3500, "bbox": [415, 154, 392, 482], "confidence": 0.98, "visible": True},
        {"t_ms": 4000, "bbox": [325, 159, 488, 466], "confidence": 0.98, "visible": True},
        {"t_ms": 4500, "bbox": [317, 0, 683, 682], "confidence": 0.98, "visible": True},
        {"t_ms": 5000, "bbox": [311, 0, 689, 764], "confidence": 0.98, "visible": True},
    ]

    can_frames = [
        {"t_ms": 0, "bbox": [407, 363, 176, 356], "confidence": 0.99, "visible": True},
        {"t_ms": 500, "bbox": [407, 362, 177, 357], "confidence": 0.99, "visible": True},
        {"t_ms": 1000, "bbox": [408, 361, 178, 358], "confidence": 0.99, "visible": True},
        {"t_ms": 1500, "bbox": [414, 353, 187, 366], "confidence": 0.99, "visible": True},
        {"t_ms": 2000, "bbox": [414, 282, 179, 437], "confidence": 0.99, "visible": True},
        {"t_ms": 2500, "bbox": [358, 300, 186, 419], "confidence": 0.99, "visible": True},
        {"t_ms": 3000, "bbox": [304, 302, 181, 417], "confidence": 0.99, "visible": True},
        {"t_ms": 3500, "bbox": [330, 149, 175, 570], "confidence": 0.98, "visible": True},
        {"t_ms": 4000, "bbox": [327, 227, 203, 492], "confidence": 0.98, "visible": True},
        {"t_ms": 4500, "bbox": [321, 221, 177, 498], "confidence": 0.98, "visible": True},
        {"t_ms": 5000, "bbox": [321, 300, 176, 419], "confidence": 0.99, "visible": True},
    ]

    actions = [
        {"phase": "idle", "t_start_ms": 0, "t_end_ms": 1000},
        {"phase": "reach", "t_start_ms": 1000, "t_end_ms": 3000},
        {"phase": "grasp", "t_start_ms": 3000, "t_end_ms": 3500},
        {"phase": "lift_and_move", "t_start_ms": 3500, "t_end_ms": 4500},
        {"phase": "place", "t_start_ms": 4500, "t_end_ms": duration_ms},
    ]

    relations = [
        {"subject": "can", "relation": "on_top_of", "object": "table", "t_start_ms": 0, "t_end_ms": 3500},
        {"subject": "right_hand", "relation": "holding", "object": "can", "t_start_ms": 3000, "t_end_ms": 4500},
        {"subject": "can", "relation": "on_top_of", "object": "table", "t_start_ms": 4500, "t_end_ms": duration_ms},
    ]

    table_y = int(height * 0.67)
    table_h = int(height * 0.33)

    # Build data objects
    run_data = {
        "run_id": "run_can_pickup_001",
        "name": "Can Pickup Demo",
        "created_at": now,
        "status": "complete",
        "target_object": "can",
        "action_label": "pick_and_place",
        "summary": {
            "source_video_count": 1,
            "tracked_object_count": 3,
            "synthetic_output_count": len([v for v in synthetic_results.values() if v.get("status") == "succeeded"]),
            "duration_ms": duration_ms,
        },
    }

    pipeline_data = {
        "pipeline_id": "pipe_front_001",
        "run_id": "run_can_pickup_001",
        "label": "Front View",
        "status": "complete",
        "source_video": {
            "video_id": "video_front_001",
            "url": "/media/source.mp4",
            "filename": "source.mp4",
            "duration_ms": duration_ms,
            "width": width,
            "height": height,
        },
        "detected_objects": [
            {"track_id": "hand_right_001", "label": "right_hand", "type": "actor_part", "color": "#35d0ff"},
            {"track_id": "can_001", "label": "can", "type": "manipulated_object", "color": "#7cf29a"},
            {"track_id": "table_001", "label": "table", "type": "support_surface", "color": "#5c5c6e"},
        ],
        "stage_status": {
            "source_video": "complete",
            "detection": "complete",
            "tracking": "complete",
            "annotations": "complete",
            "world_model": "complete",
            "synthetic_outputs": "complete",
        },
    }

    tracks_data = [
        {
            "track_id": "hand_right_001",
            "pipeline_id": "pipe_front_001",
            "label": "right_hand",
            "type": "actor_part",
            "color": "#35d0ff",
            "frames": hand_frames,
        },
        {
            "track_id": "can_001",
            "pipeline_id": "pipe_front_001",
            "label": "can",
            "type": "manipulated_object",
            "color": "#7cf29a",
            "frames": can_frames,
        },
        {
            "track_id": "table_001",
            "pipeline_id": "pipe_front_001",
            "label": "table",
            "type": "support_surface",
            "color": "#5c5c6e",
            "frames": [
                {"t_ms": 0, "bbox": [0, table_y, width, table_h], "confidence": 0.98, "visible": True},
                {"t_ms": duration_ms, "bbox": [0, table_y, width, table_h], "confidence": 0.98, "visible": True},
            ],
        },
    ]

    world_model_data = {
        "world_model_id": "wm_pipe_front_001",
        "pipeline_id": "pipe_front_001",
        "target_object": "can",
        "action_label": "pick_and_place",
        "duration_ms": duration_ms,
        "objects": [
            {"id": "hand_right_001", "label": "right_hand", "role": "actor"},
            {"id": "can_001", "label": "can", "role": "manipulated_object"},
            {"id": "table_001", "label": "table", "role": "support_surface"},
        ],
        "actions": actions,
        "relations": relations,
    }

    synthetic_outputs_data = []
    for var in VARIATIONS:
        sr = synthetic_results.get(var["id"], {"status": "failed"})
        filename = synthetic_video_files.get(var["id"], "")
        synthetic_outputs_data.append({
            "synthetic_id": f"synth_{var['id']}_001",
            "pipeline_id": "pipe_front_001",
            "run_id": "run_can_pickup_001",
            "label": var["label"],
            "status": sr.get("status", "failed"),
            "provider": "seedance_1_5_pro",
            "prompt": var["prompt"],
            "constraints": [
                "preserve same target object: can",
                "preserve same action phase order",
                "preserve same approximate timing",
                "preserve same task outcome",
            ],
            "video_url": f"/media/{filename}" if filename else "",
            "created_at": now,
        })

    # Write JS file
    js_path = Path(__file__).parent.parent / "dashboard" / "src" / "data" / "seedRun.js"

    annotation_frames_code = """
// Annotation frames derived from tracks and world model
export const annotationFrames = worldModel.actions.flatMap((action) => {
  const frames = [];
  for (let t = action.t_start_ms; t < action.t_end_ms; t += 200) {
    const handTrack = tracks[0].frames.find((f) => f.t_ms === t) || tracks[0].frames.find((f) => f.t_ms <= t);
    const canTrack = tracks[1].frames.find((f) => f.t_ms === t) || tracks[1].frames.find((f) => f.t_ms <= t);
    const relations = [];
    for (const rel of worldModel.relations) {
      if (t >= rel.t_start_ms && t < rel.t_end_ms) {
        relations.push({ subject: rel.subject, relation: rel.relation, object: rel.object });
      }
    }
    frames.push({
      pipeline_id: "pipe_front_001",
      t_ms: t,
      active_action_phase: action.phase,
      objects: [
        handTrack && { track_id: "hand_right_001", label: "right_hand", bbox: handTrack.bbox, confidence: handTrack.confidence },
        canTrack && { track_id: "can_001", label: "can", bbox: canTrack.bbox, confidence: canTrack.confidence },
      ].filter(Boolean),
      relations,
    });
  }
  return frames;
});
"""

    lines = [
        "// Auto-generated by pipeline - real data from BytePlus API",
        "// Source video: Seedance 1.5 Pro",
        "// Detection: seed-2-0-pro-260328 (BytePlus Vision)",
        "// Action labeling: seed-2-0-lite-260228 (BytePlus LLM)",
        f"// Generated: {now}",
        "",
        f"export const run = {json.dumps(run_data, indent=2)};",
        "",
        f"export const pipeline = {json.dumps(pipeline_data, indent=2)};",
        "",
        f"export const tracks = {json.dumps(tracks_data, indent=2)};",
        "",
        f"export const worldModel = {json.dumps(world_model_data, indent=2)};",
        "",
        f"export const syntheticOutputs = {json.dumps(synthetic_outputs_data, indent=2)};",
        "",
        annotation_frames_code,
    ]

    with open(js_path, "w") as f:
        f.write("\n".join(lines))

    print(f"  Seed JS updated: {js_path}")

    # Also write raw JSON for reference
    seed_json = {
        "run": run_data,
        "pipeline": pipeline_data,
        "tracks": tracks_data,
        "worldModel": world_model_data,
        "syntheticOutputs": synthetic_outputs_data,
    }
    json_path = OUTPUT_DIR / "seed_data.json"
    with open(json_path, "w") as f:
        json.dump(seed_json, f, indent=2)
    print(f"  Seed JSON written: {json_path}")


if __name__ == "__main__":
    main()

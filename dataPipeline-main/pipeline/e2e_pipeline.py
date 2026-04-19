"""
E2E Data Pipeline

Generates all seed data for the dashboard demo:
1. Generate source video via Seedance
2. Extract frames from source video
3. Run object detection on each frame via BytePlus Vision API
4. Build object tracks from detections
5. Generate action labels via BytePlus LLM
6. Assemble world model
7. Generate synthetic variations via Seedance
8. Poll for completion and download videos
9. Output seed data JSON + downloaded videos

Usage:
    pip install -r requirements.txt
    # Set ARK_API_KEY in .env
    python e2e_pipeline.py

Output:
    output/
      seed_data.json          - complete seed data for dashboard
      source.mp4              - source video
      synthetic_warehouse.mp4 - synthetic variation 1
      synthetic_kitchen.mp4   - synthetic variation 2
      synthetic_outdoor.mp4   - synthetic variation 3
"""

import os
import sys
import json
import time
import base64
import shutil
import requests
import cv2
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# --- Config ---
ARK_API_KEY = os.getenv("ARK_API_KEY")
if not ARK_API_KEY:
    print("ERROR: Set ARK_API_KEY in .env file")
    sys.exit(1)

from byteplussdkarkruntime import Ark

client = Ark(
    base_url="https://ark.ap-southeast.bytepluses.com/api/v3",
    api_key=ARK_API_KEY,
)

OUTPUT_DIR = Path(__file__).parent / "output"
DASHBOARD_MEDIA_DIR = Path(__file__).parent.parent / "dashboard" / "public" / "media"

VISION_MODEL = "seed-2-0-pro-260328"
LLM_MODEL = "seed-2-0-lite-260228"
SEEDANCE_MODEL = "seedance-1-5-pro-251215"

TARGET_OBJECT = "can"
ACTION_LABEL = "pick_and_place"

# --- Helpers ---

def extract_text(response):
    """Extract text from BytePlus response object."""
    if hasattr(response, 'output'):
        output = response.output
        if isinstance(output, list):
            texts = []
            for item in output:
                if hasattr(item, 'content') and isinstance(item.content, list):
                    for c in item.content:
                        if hasattr(c, 'text'):
                            texts.append(c.text)
                elif hasattr(item, 'content') and isinstance(item.content, str):
                    texts.append(item.content)
                elif hasattr(item, 'text'):
                    texts.append(item.text)
            if texts:
                return '\n'.join(texts)
        elif isinstance(output, str):
            return output
    return str(response)


def parse_json_response(text):
    """Parse JSON from LLM response, handling markdown code blocks."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)


def download_video(url, dest_path):
    """Download video from URL to local path."""
    print(f"  Downloading to {dest_path.name}...")
    r = requests.get(url, stream=True, timeout=120)
    r.raise_for_status()
    with open(dest_path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"  Downloaded {dest_path.stat().st_size / 1024:.0f} KB")


# --- Step 1: Generate Source Video ---

def generate_source_video():
    """Generate a source video of a hand picking up a can using Seedance."""
    print("\n=== STEP 1: Generate Source Video via Seedance ===")

    prompt = (
        "A realistic close-up video of a human right hand reaching for a soda can "
        "on a plain wooden table, grasping it, lifting it up, moving it to the left, "
        "and placing it back down on the table. The camera is stationary, front view. "
        "Neutral lighting, clean background. The motion is smooth and deliberate."
    )

    print(f"  Prompt: {prompt[:80]}...")
    result = client.content_generation.tasks.create(
        model=SEEDANCE_MODEL,
        content=[{"type": "text", "text": prompt}],
        generate_audio=False,
        ratio="16:9",
        duration=5,
        watermark=False,
    )
    task_id = result.id
    print(f"  Task ID: {task_id}")

    return poll_seedance_task(task_id, "source video")


def poll_seedance_task(task_id, label):
    """Poll a Seedance task until completion."""
    print(f"  Polling {label}...")
    for attempt in range(40):  # up to ~10 min
        time.sleep(15)
        result = client.content_generation.tasks.get(task_id=task_id)
        d = result.to_dict()
        status = d.get("status", "unknown")
        print(f"  [{attempt+1}] Status: {status}")

        if status == "succeeded":
            video_url = d.get("content", {}).get("video_url", "")
            print(f"  {label} ready!")
            return video_url
        elif status == "failed":
            print(f"  ERROR: {label} generation failed")
            print(f"  Details: {json.dumps(d, indent=2)}")
            return None

    print(f"  TIMEOUT: {label} did not complete in time")
    return None


# --- Step 2: Extract Frames ---

def extract_frames(video_path, interval_ms=500):
    """Extract frames from video at given interval."""
    print(f"\n=== STEP 2: Extract Frames (every {interval_ms}ms) ===")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"  ERROR: Cannot open {video_path}")
        return [], 0, 0, 0

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration_ms = int((total_frames / fps) * 1000) if fps > 0 else 0

    print(f"  Video: {width}x{height}, {fps:.1f}fps, {duration_ms}ms, {total_frames} frames")

    frames = []
    for t_ms in range(0, duration_ms + 1, interval_ms):
        frame_idx = int((t_ms / 1000) * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            break

        # Encode as JPEG base64
        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        b64 = base64.b64encode(buf).decode('utf-8')
        frames.append({"t_ms": t_ms, "base64": b64})

    cap.release()
    print(f"  Extracted {len(frames)} frames")
    return frames, duration_ms, width, height


# --- Step 3: Object Detection ---

def detect_objects_in_frame(frame_b64, object_name):
    """Detect an object in a frame using BytePlus Vision API."""
    data_url = f"data:image/jpeg;base64,{frame_b64}"

    prompt = f"""You are an object detection assistant.
Find the "{object_name}" in this image.
Return ONLY a JSON object:
{{"found": true, "label": "{object_name}", "bbox": [x, y, width, height], "confidence": 0.0-1.0}}
where bbox is pixel coordinates.
If not found return {{"found": false}}.
No other text."""

    response = client.responses.create(
        model=VISION_MODEL,
        input=[{
            "role": "user",
            "content": [
                {"type": "input_image", "image_url": data_url},
                {"type": "input_text", "text": prompt},
            ],
        }],
    )
    text = extract_text(response)
    return parse_json_response(text)


def run_detection(frames, width, height):
    """Run object detection on all frames for hands and target object."""
    print(f"\n=== STEP 3: Object Detection ({len(frames)} frames) ===")

    hand_detections = []
    object_detections = []

    for i, frame in enumerate(frames):
        t_ms = frame["t_ms"]
        print(f"  Frame {i+1}/{len(frames)} (t={t_ms}ms)...")

        # Detect hand
        try:
            hand_result = detect_objects_in_frame(frame["base64"], "right hand")
            if hand_result.get("found"):
                hand_detections.append({
                    "t_ms": t_ms,
                    "bbox": hand_result["bbox"],
                    "confidence": hand_result.get("confidence", 0.9),
                    "visible": True,
                })
                print(f"    Hand: {hand_result['bbox']} ({hand_result.get('confidence', 0):.0%})")
            else:
                hand_detections.append({"t_ms": t_ms, "bbox": [0, 0, 0, 0], "confidence": 0, "visible": False})
                print(f"    Hand: not found")
        except Exception as e:
            print(f"    Hand detection error: {e}")
            hand_detections.append({"t_ms": t_ms, "bbox": [0, 0, 0, 0], "confidence": 0, "visible": False})

        # Detect target object
        try:
            obj_result = detect_objects_in_frame(frame["base64"], TARGET_OBJECT)
            if obj_result.get("found"):
                object_detections.append({
                    "t_ms": t_ms,
                    "bbox": obj_result["bbox"],
                    "confidence": obj_result.get("confidence", 0.9),
                    "visible": True,
                })
                print(f"    {TARGET_OBJECT}: {obj_result['bbox']} ({obj_result.get('confidence', 0):.0%})")
            else:
                object_detections.append({"t_ms": t_ms, "bbox": [0, 0, 0, 0], "confidence": 0, "visible": False})
                print(f"    {TARGET_OBJECT}: not found")
        except Exception as e:
            print(f"    {TARGET_OBJECT} detection error: {e}")
            object_detections.append({"t_ms": t_ms, "bbox": [0, 0, 0, 0], "confidence": 0, "visible": False})

        # Throttle — API takes 3-6s per call, two calls per frame
        # No extra sleep needed, the API calls themselves provide the delay

    return hand_detections, object_detections


# --- Step 4: Action Labeling ---

def generate_action_labels(object_detections, duration_ms):
    """Generate action phase labels from trajectory data using LLM."""
    print(f"\n=== STEP 4: Action Labeling ===")

    trajectory = [
        {"t": d["t_ms"], "center": [d["bbox"][0] + d["bbox"][2]//2, d["bbox"][1] + d["bbox"][3]//2]}
        for d in object_detections if d["visible"]
    ]

    prompt = f"""Object: {TARGET_OBJECT}. Duration: {duration_ms}ms.
Trajectory: {json.dumps(trajectory)}
Label action phases. Return ONLY JSON:
{{"actions": [{{"t_start_ms": 0, "t_end_ms": 500, "phase": "idle"}}, ...]}}
Phases: idle, reach, grasp, lift_and_move, place.
The phases must cover the full duration from 0 to {duration_ms}ms with no gaps.
No other text."""

    response = client.responses.create(model=LLM_MODEL, input=prompt)
    text = extract_text(response)
    result = parse_json_response(text)

    actions = result.get("actions", [])
    print(f"  Found {len(actions)} action phases:")
    for a in actions:
        print(f"    {a['phase']}: {a['t_start_ms']}ms - {a['t_end_ms']}ms")

    return actions


# --- Step 5: Build World Model ---

def build_world_model(actions, duration_ms):
    """Assemble the world model from tracks and actions."""
    print(f"\n=== STEP 5: Build World Model ===")

    # Infer relations from actions
    relations = []

    # Find grasp phase — before grasp, can is on table
    grasp = next((a for a in actions if a["phase"] == "grasp"), None)
    place = next((a for a in actions if a["phase"] == "place"), None)
    lift = next((a for a in actions if a["phase"] == "lift_and_move"), None)

    if grasp:
        relations.append({
            "subject": TARGET_OBJECT,
            "relation": "on_top_of",
            "object": "table",
            "t_start_ms": 0,
            "t_end_ms": grasp["t_end_ms"],
        })

    if grasp and place:
        relations.append({
            "subject": "right_hand",
            "relation": "holding",
            "object": TARGET_OBJECT,
            "t_start_ms": grasp["t_start_ms"],
            "t_end_ms": place["t_start_ms"],
        })

    if place:
        relations.append({
            "subject": TARGET_OBJECT,
            "relation": "on_top_of",
            "object": "table",
            "t_start_ms": place["t_start_ms"],
            "t_end_ms": duration_ms,
        })

    wm = {
        "world_model_id": "wm_pipe_front_001",
        "pipeline_id": "pipe_front_001",
        "target_object": TARGET_OBJECT,
        "action_label": ACTION_LABEL,
        "duration_ms": duration_ms,
        "objects": [
            {"id": "hand_right_001", "label": "right_hand", "role": "actor"},
            {"id": "can_001", "label": TARGET_OBJECT, "role": "manipulated_object"},
            {"id": "table_001", "label": "table", "role": "support_surface"},
        ],
        "actions": actions,
        "relations": relations,
    }

    print(f"  Objects: {len(wm['objects'])}")
    print(f"  Actions: {len(wm['actions'])}")
    print(f"  Relations: {len(wm['relations'])}")

    return wm


# --- Step 6: Generate Synthetic Variations ---

VARIATIONS = [
    {
        "id": "warehouse",
        "label": "Warehouse",
        "prompt": (
            "A hand picks up a metallic can from a workbench in an industrial warehouse "
            "with concrete floors and metal shelving. The motion follows the same "
            "reach-grasp-lift-move-place sequence. Lighting is overhead fluorescent."
        ),
    },
    {
        "id": "kitchen",
        "label": "Kitchen Counter",
        "prompt": (
            "A hand picks up an aluminum can from a modern kitchen counter with marble surface. "
            "Same pick-and-place action with warm interior lighting and kitchen appliances in background."
        ),
    },
    {
        "id": "outdoor",
        "label": "Outdoor Picnic",
        "prompt": (
            "A hand picks up a soda can from a wooden picnic table in an outdoor park setting. "
            "Natural daylight, grass and trees in background. Same reach-grasp-lift-move-place motion."
        ),
    },
]


def generate_synthetic_outputs(source_video_url):
    """Submit Seedance generation jobs for all variations."""
    print(f"\n=== STEP 6: Generate Synthetic Variations ===")

    jobs = []
    for var in VARIATIONS:
        print(f"  Submitting: {var['label']}...")

        # seedance-1-5-pro only supports text-to-video (t2v), not reference video (r2v)
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

    return jobs


def poll_synthetic_jobs(jobs):
    """Poll all synthetic generation jobs until completion."""
    print(f"\n=== STEP 7: Poll Synthetic Jobs ===")

    results = {}
    pending = list(jobs)

    for attempt in range(40):  # ~10 min max
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
                results[job["variation"]["id"]] = {
                    "status": "succeeded",
                    "video_url": video_url,
                }
            elif status == "failed":
                print(f"  [{attempt+1}] {label}: FAILED")
                results[job["variation"]["id"]] = {"status": "failed", "video_url": ""}
            else:
                print(f"  [{attempt+1}] {label}: {status}")
                still_pending.append(job)

        pending = still_pending

    # Mark any remaining as timed out
    for job in pending:
        results[job["variation"]["id"]] = {"status": "failed", "video_url": ""}
        print(f"  TIMEOUT: {job['variation']['label']}")

    return results


# --- Step 8: Assemble Seed Data ---

def assemble_seed_data(
    duration_ms, width, height,
    hand_detections, object_detections,
    world_model, synthetic_results,
    source_video_local, synthetic_video_locals,
):
    """Assemble the complete seed data JSON."""
    print(f"\n=== STEP 8: Assemble Seed Data ===")

    now = datetime.now(timezone.utc).isoformat()

    # Build tracks
    tracks = [
        {
            "track_id": "hand_right_001",
            "pipeline_id": "pipe_front_001",
            "label": "right_hand",
            "type": "actor_part",
            "color": "#35d0ff",
            "frames": hand_detections,
        },
        {
            "track_id": "can_001",
            "pipeline_id": "pipe_front_001",
            "label": TARGET_OBJECT,
            "type": "manipulated_object",
            "color": "#7cf29a",
            "frames": object_detections,
        },
        {
            "track_id": "table_001",
            "pipeline_id": "pipe_front_001",
            "label": "table",
            "type": "support_surface",
            "color": "#5c5c6e",
            "frames": [
                {"t_ms": 0, "bbox": [0, int(height * 0.67), width, int(height * 0.33)], "confidence": 0.98, "visible": True},
                {"t_ms": duration_ms, "bbox": [0, int(height * 0.67), width, int(height * 0.33)], "confidence": 0.98, "visible": True},
            ],
        },
    ]

    # Build synthetic outputs
    synthetic_outputs = []
    for var in VARIATIONS:
        sr = synthetic_results.get(var["id"], {"status": "failed", "video_url": ""})
        local_video = synthetic_video_locals.get(var["id"], "")

        synthetic_outputs.append({
            "synthetic_id": f"synth_{var['id']}_001",
            "pipeline_id": "pipe_front_001",
            "run_id": "run_can_pickup_001",
            "label": var["label"],
            "status": sr["status"],
            "provider": "seedance_1_5_pro",
            "prompt": var["prompt"],
            "constraints": [
                f"preserve same target object: {TARGET_OBJECT}",
                "preserve same action phase order",
                "preserve same approximate timing",
                "preserve same task outcome",
            ],
            "video_url": f"/media/{local_video}" if local_video else "",
            "created_at": now,
        })

    seed = {
        "run": {
            "run_id": "run_can_pickup_001",
            "name": "Can Pickup Demo",
            "created_at": now,
            "status": "complete",
            "target_object": TARGET_OBJECT,
            "action_label": ACTION_LABEL,
            "summary": {
                "source_video_count": 1,
                "tracked_object_count": 3,
                "synthetic_output_count": len([s for s in synthetic_outputs if s["status"] == "succeeded"]),
                "duration_ms": duration_ms,
            },
        },
        "pipeline": {
            "pipeline_id": "pipe_front_001",
            "run_id": "run_can_pickup_001",
            "label": "Front View",
            "status": "complete",
            "source_video": {
                "video_id": "video_front_001",
                "url": f"/media/{source_video_local}" if source_video_local else "",
                "filename": source_video_local or "source.mp4",
                "duration_ms": duration_ms,
                "width": width,
                "height": height,
            },
            "detected_objects": [
                {"track_id": "hand_right_001", "label": "right_hand", "type": "actor_part", "color": "#35d0ff"},
                {"track_id": "can_001", "label": TARGET_OBJECT, "type": "manipulated_object", "color": "#7cf29a"},
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
        },
        "tracks": tracks,
        "worldModel": world_model,
        "syntheticOutputs": synthetic_outputs,
    }

    return seed


# --- Main ---

def main():
    print("=" * 60)
    print("  Data Pipeline — E2E Seed Data Generator")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DASHBOARD_MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Generate source video
    source_video_url = generate_source_video()
    if not source_video_url:
        print("\nFATAL: Could not generate source video. Exiting.")
        sys.exit(1)

    source_path = OUTPUT_DIR / "source.mp4"
    download_video(source_video_url, source_path)

    # Copy to dashboard media
    dashboard_source = DASHBOARD_MEDIA_DIR / "source.mp4"
    shutil.copy2(source_path, dashboard_source)
    print(f"  Copied to {dashboard_source}")

    # Step 2: Extract frames
    frames, duration_ms, width, height = extract_frames(source_path, interval_ms=500)
    if not frames:
        print("\nFATAL: Could not extract frames. Exiting.")
        sys.exit(1)

    # Step 3: Object detection
    hand_detections, object_detections = run_detection(frames, width, height)

    # Step 4: Action labeling
    actions = generate_action_labels(object_detections, duration_ms)

    # Step 5: World model
    world_model = build_world_model(actions, duration_ms)

    # Step 6 & 7: Synthetic generation
    jobs = generate_synthetic_outputs(source_video_url)
    synthetic_results = poll_synthetic_jobs(jobs)

    # Download synthetic videos
    synthetic_video_locals = {}
    for var in VARIATIONS:
        sr = synthetic_results.get(var["id"], {})
        if sr.get("status") == "succeeded" and sr.get("video_url"):
            filename = f"synthetic_{var['id']}.mp4"
            local_path = OUTPUT_DIR / filename
            download_video(sr["video_url"], local_path)
            # Copy to dashboard
            shutil.copy2(local_path, DASHBOARD_MEDIA_DIR / filename)
            synthetic_video_locals[var["id"]] = filename

    # Step 8: Assemble seed data
    seed_data = assemble_seed_data(
        duration_ms, width, height,
        hand_detections, object_detections,
        world_model, synthetic_results,
        "source.mp4", synthetic_video_locals,
    )

    # Write seed data JSON
    seed_json_path = OUTPUT_DIR / "seed_data.json"
    with open(seed_json_path, "w") as f:
        json.dump(seed_data, f, indent=2)
    print(f"\n  Seed data written to {seed_json_path}")

    # Also write as JS module for dashboard import
    js_path = Path(__file__).parent.parent / "dashboard" / "src" / "data" / "seedRun.js"
    write_seed_js(seed_data, js_path)
    print(f"  Dashboard seed JS written to {js_path}")

    print("\n" + "=" * 60)
    print("  PIPELINE COMPLETE")
    print(f"  Source video: {source_path}")
    print(f"  Seed data: {seed_json_path}")
    print(f"  Synthetic videos: {len(synthetic_video_locals)}")
    print("=" * 60)


def write_seed_js(data, path):
    """Write seed data as a JS module the dashboard can import."""

    def to_js(obj, indent=0):
        return json.dumps(obj, indent=2)

    content = f"""// Auto-generated by e2e_pipeline.py — do not edit manually
// Generated at {datetime.now(timezone.utc).isoformat()}

export const run = {to_js(data['run'])};

export const pipeline = {to_js(data['pipeline'])};

export const tracks = {to_js(data['tracks'])};

export const worldModel = {to_js(data['worldModel'])};

export const syntheticOutputs = {to_js(data['syntheticOutputs'])};

// Annotation frames derived from tracks and world model
export const annotationFrames = worldModel.actions.flatMap((action) => {{
  const frames = [];
  for (let t = action.t_start_ms; t < action.t_end_ms; t += 200) {{
    const handTrack = tracks[0].frames.find((f) => f.t_ms === t) || tracks[0].frames.find((f) => f.t_ms <= t);
    const canTrack = tracks[1].frames.find((f) => f.t_ms === t) || tracks[1].frames.find((f) => f.t_ms <= t);
    const relations = [];
    for (const rel of worldModel.relations) {{
      if (t >= rel.t_start_ms && t < rel.t_end_ms) {{
        relations.push({{ subject: rel.subject, relation: rel.relation, object: rel.object }});
      }}
    }}
    frames.push({{
      pipeline_id: "pipe_front_001",
      t_ms: t,
      active_action_phase: action.phase,
      objects: [
        handTrack && {{ track_id: "hand_right_001", label: "right_hand", bbox: handTrack.bbox, confidence: handTrack.confidence }},
        canTrack && {{ track_id: "can_001", label: "{data['run']['target_object']}", bbox: canTrack.bbox, confidence: canTrack.confidence }},
      ].filter(Boolean),
      relations,
    }});
  }}
  return frames;
}});
"""
    with open(path, "w") as f:
        f.write(content)


if __name__ == "__main__":
    main()

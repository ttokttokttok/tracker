"""
Full pipeline regeneration:
1. Generate new source video (realistic lift-and-place, not can opening)
2. Run detection + action labeling on new source
3. Generate synthetics using Seedance 2.0 with source as reference video (v2v)
   Falls back to Seedance 1.5 text-only if 2.0 queue is stuck
4. Update dashboard seed data
"""

import os, sys, json, time, base64, shutil, requests, cv2
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
SEED_JS = Path(__file__).parent.parent / "dashboard" / "src" / "data" / "seedRun.js"

VISION_MODEL = "seed-2-0-pro-260328"
LLM_MODEL = "seed-2-0-lite-260228"
SEEDANCE_15 = "seedance-1-5-pro-251215"
SEEDANCE_20 = "dreamina-seedance-2-0-260128"

# Tunnel URL so Seedance can fetch our source video
TUNNEL_BASE = "https://assist-leading-vocal-southwest.trycloudflare.com"

TARGET_OBJECT = "can"
ACTION_LABEL = "pick_and_place"


def extract_text(response):
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


def parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        lines = [l for l in text.split("\n") if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)


def download_video(url, dest):
    print(f"  Downloading {dest.name}...")
    r = requests.get(url, stream=True, timeout=120)
    r.raise_for_status()
    with open(dest, 'wb') as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)
    print(f"  {dest.stat().st_size / 1024:.0f} KB")


def poll_task(task_id, label, max_polls=40, interval=15):
    for i in range(max_polls):
        time.sleep(interval)
        d = client.content_generation.tasks.get(task_id=task_id).to_dict()
        s = d.get("status", "?")
        print(f"  [{i+1}] {label}: {s}")
        if s == "succeeded":
            return d.get("content", {}).get("video_url", "")
        if s == "failed":
            return None
    return None


# ─── STEP 1: New source video ───

def gen_source_video():
    print("\n=== STEP 1: Generate Source Video ===")
    prompt = (
        "A person's right hand reaches across a wooden desk, picks up a small "
        "aluminum soda can by wrapping fingers around it, lifts it a few inches "
        "off the desk, moves it about six inches to the left, and gently sets it "
        "back down on the desk. The camera is fixed, eye-level, looking straight "
        "at the desk from the front. Simple neutral background, soft natural "
        "lighting. Realistic hand motion, no exaggerated movements."
    )
    print(f"  Prompt: {prompt[:80]}...")
    r = client.content_generation.tasks.create(
        model=SEEDANCE_15,
        content=[{"type": "text", "text": prompt}],
        generate_audio=False, ratio="16:9", duration=5, watermark=False,
    )
    print(f"  Task: {r.id}")
    return poll_task(r.id, "source video")


# ─── STEP 2: Detection ───

def detect(frame_b64, obj_name):
    data_url = f"data:image/jpeg;base64,{frame_b64}"
    prompt = f'You are an object detection assistant.\nFind the "{obj_name}" in this image.\nReturn ONLY a JSON object:\n{{"found": true, "label": "{obj_name}", "bbox": [x, y, width, height], "confidence": 0.0-1.0}}\nwhere bbox is pixel coordinates.\nIf not found return {{"found": false}}.\nNo other text.'
    resp = client.responses.create(
        model=VISION_MODEL,
        input=[{"role": "user", "content": [
            {"type": "input_image", "image_url": data_url},
            {"type": "input_text", "text": prompt},
        ]}],
    )
    return parse_json(extract_text(resp))


def run_detection(video_path):
    print("\n=== STEP 2: Extract Frames + Detect ===")
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    dur = int((total / fps) * 1000) if fps > 0 else 5000
    print(f"  Video: {w}x{h}, {fps:.0f}fps, {dur}ms")

    hand_frames, can_frames = [], []
    interval = 500

    for t_ms in range(0, dur + 1, interval):
        idx = int((t_ms / 1000) * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            break
        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        b64 = base64.b64encode(buf).decode()

        print(f"  Frame t={t_ms}ms...")
        # Hand
        try:
            hr = detect(b64, "right hand")
            if hr.get("found"):
                hand_frames.append({"t_ms": t_ms, "bbox": hr["bbox"], "confidence": hr.get("confidence", 0.9), "visible": True})
                print(f"    hand: {hr['bbox']}")
            else:
                hand_frames.append({"t_ms": t_ms, "bbox": [0,0,0,0], "confidence": 0, "visible": False})
                print(f"    hand: not found")
        except Exception as e:
            hand_frames.append({"t_ms": t_ms, "bbox": [0,0,0,0], "confidence": 0, "visible": False})
            print(f"    hand err: {e}")

        # Can
        try:
            cr = detect(b64, TARGET_OBJECT)
            if cr.get("found"):
                can_frames.append({"t_ms": t_ms, "bbox": cr["bbox"], "confidence": cr.get("confidence", 0.9), "visible": True})
                print(f"    can: {cr['bbox']}")
            else:
                can_frames.append({"t_ms": t_ms, "bbox": [0,0,0,0], "confidence": 0, "visible": False})
                print(f"    can: not found")
        except Exception as e:
            can_frames.append({"t_ms": t_ms, "bbox": [0,0,0,0], "confidence": 0, "visible": False})
            print(f"    can err: {e}")

    cap.release()
    return hand_frames, can_frames, dur, w, h


# ─── STEP 3: Action labeling ───

def label_actions(can_frames, dur):
    print("\n=== STEP 3: Action Labeling ===")
    traj = [{"t": f["t_ms"], "center": [f["bbox"][0]+f["bbox"][2]//2, f["bbox"][1]+f["bbox"][3]//2]}
            for f in can_frames if f["visible"]]
    prompt = f'Object: {TARGET_OBJECT}. Duration: {dur}ms.\nTrajectory: {json.dumps(traj)}\nLabel action phases. Return ONLY JSON:\n{{"actions": [{{"t_start_ms": 0, "t_end_ms": 500, "phase": "idle"}}, ...]}}\nPhases: idle, reach, grasp, lift_and_move, place.\nThe phases must cover 0 to {dur}ms with no gaps.\nNo other text.'
    resp = client.responses.create(model=LLM_MODEL, input=prompt)
    result = parse_json(extract_text(resp))
    actions = result.get("actions", [])
    for a in actions:
        print(f"  {a['phase']}: {a['t_start_ms']}-{a['t_end_ms']}ms")
    return actions


# ─── STEP 4: Synthetic (v2v with Seedance 2.0, fallback to 1.5 t2v) ───

VARIATIONS = [
    {
        "id": "warehouse",
        "label": "Warehouse",
        "prompt": (
            "Recreate the exact same hand motion from the reference video, but in an "
            "industrial warehouse setting. A hand lifts a can from a metal workbench "
            "and places it back down. Concrete floor, metal shelving, fluorescent lights."
        ),
    },
    {
        "id": "kitchen",
        "label": "Kitchen Counter",
        "prompt": (
            "Recreate the exact same hand motion from the reference video, but on a "
            "marble kitchen counter. A hand lifts a can and places it back down. "
            "Modern kitchen with warm lighting, appliances in background."
        ),
    },
    {
        "id": "outdoor",
        "label": "Outdoor Picnic",
        "prompt": (
            "Recreate the exact same hand motion from the reference video, but on a "
            "wooden picnic table outdoors. A hand lifts a can and places it back down. "
            "Park setting, natural daylight, grass and trees in background."
        ),
    },
]


def gen_synthetics(source_public_url):
    print("\n=== STEP 4: Generate Synthetics (trying Seedance 2.0 v2v) ===")

    # Try Seedance 2.0 with reference video first
    jobs = []
    use_20 = True

    for v in VARIATIONS:
        print(f"  Submitting {v['label']} (Seedance 2.0 + ref video)...")
        try:
            content = [
                {"type": "text", "text": v["prompt"]},
                {"type": "video_url", "video_url": {"url": source_public_url}, "role": "reference_video"},
            ]
            r = client.content_generation.tasks.create(
                model=SEEDANCE_20,
                content=content,
                generate_audio=False, ratio="16:9", duration=5, watermark=False,
            )
            print(f"    Task: {r.id}")
            jobs.append({"task_id": r.id, "var": v, "model": "2.0"})
        except Exception as e:
            print(f"    Seedance 2.0 failed: {e}")
            print(f"    Falling back to Seedance 1.5 text-only...")
            use_20 = False
            break

    # If 2.0 failed to submit, use 1.5 for all
    if not use_20:
        jobs = []
        for v in VARIATIONS:
            # Replace "reference video" language with explicit description
            fallback_prompt = v["prompt"].replace(
                "the exact same hand motion from the reference video, but",
                "a person's hand reaching, lifting a soda can a few inches, moving it to the left, and placing it back down"
            )
            print(f"  Submitting {v['label']} (Seedance 1.5 text-only)...")
            r = client.content_generation.tasks.create(
                model=SEEDANCE_15,
                content=[{"type": "text", "text": fallback_prompt}],
                generate_audio=False, ratio="16:9", duration=5, watermark=False,
            )
            print(f"    Task: {r.id}")
            jobs.append({"task_id": r.id, "var": v, "model": "1.5"})

    # Poll — if 2.0 jobs stay queued for >3 min, abandon and resubmit with 1.5
    print("\n  Polling...")
    results = {}
    pending = list(jobs)
    stuck_count = 0

    for attempt in range(40):
        if not pending:
            break
        time.sleep(15)
        still = []
        all_queued = True

        for j in pending:
            d = client.content_generation.tasks.get(task_id=j["task_id"]).to_dict()
            s = d.get("status", "?")
            if s == "succeeded":
                print(f"  [{attempt+1}] {j['var']['label']}: DONE ({j['model']})")
                results[j["var"]["id"]] = d.get("content", {}).get("video_url", "")
                all_queued = False
            elif s == "failed":
                print(f"  [{attempt+1}] {j['var']['label']}: FAILED")
                results[j["var"]["id"]] = ""
                all_queued = False
            else:
                print(f"  [{attempt+1}] {j['var']['label']}: {s} ({j['model']})")
                still.append(j)
                if s != "queued":
                    all_queued = False

        pending = still

        # If all remaining jobs are stuck in 'queued' after 3 min, fall back to 1.5
        if all_queued and len(still) > 0 and j["model"] == "2.0":
            stuck_count += 1
            if stuck_count >= 12:  # 12 * 15s = 3 min
                print(f"\n  Seedance 2.0 queue stuck. Falling back to 1.5...")
                pending = []
                for j in still:
                    v = j["var"]
                    fallback_prompt = v["prompt"].replace(
                        "the exact same hand motion from the reference video, but",
                        "a person's hand reaching, lifting a soda can a few inches, moving it to the left, and placing it back down"
                    )
                    r = client.content_generation.tasks.create(
                        model=SEEDANCE_15,
                        content=[{"type": "text", "text": fallback_prompt}],
                        generate_audio=False, ratio="16:9", duration=5, watermark=False,
                    )
                    print(f"    Resubmitted {v['label']} on 1.5: {r.id}")
                    pending.append({"task_id": r.id, "var": v, "model": "1.5"})
                stuck_count = 0
        else:
            stuck_count = 0

    for j in pending:
        results[j["var"]["id"]] = ""

    return results


# ─── STEP 5: Assemble + write ───

def write_seed(hand_frames, can_frames, actions, dur, w, h, syn_results):
    print("\n=== STEP 5: Write Seed Data ===")
    now = datetime.now(timezone.utc).isoformat()
    table_y, table_h = int(h * 0.67), int(h * 0.33)

    relations = []
    grasp = next((a for a in actions if a["phase"] == "grasp"), None)
    place = next((a for a in actions if a["phase"] == "place"), None)
    if grasp:
        relations.append({"subject": "can", "relation": "on_top_of", "object": "table", "t_start_ms": 0, "t_end_ms": grasp["t_end_ms"]})
    if grasp and place:
        relations.append({"subject": "right_hand", "relation": "holding", "object": "can", "t_start_ms": grasp["t_start_ms"], "t_end_ms": place["t_start_ms"]})
    if place:
        relations.append({"subject": "can", "relation": "on_top_of", "object": "table", "t_start_ms": place["t_start_ms"], "t_end_ms": dur})

    syn_outputs = []
    for v in VARIATIONS:
        url = syn_results.get(v["id"], "")
        fname = f"synthetic_{v['id']}.mp4" if url else ""
        syn_outputs.append({
            "synthetic_id": f"synth_{v['id']}_001",
            "pipeline_id": "pipe_front_001",
            "run_id": "run_can_pickup_001",
            "label": v["label"],
            "status": "succeeded" if url else "failed",
            "provider": "seedance",
            "prompt": v["prompt"],
            "constraints": ["preserve same action: lift and place can", "preserve varied environment", "video-to-video reference"],
            "video_url": f"/media/{fname}" if fname else "",
            "created_at": now,
        })

    run_data = {"run_id": "run_can_pickup_001", "name": "Can Pickup Demo", "created_at": now, "status": "complete", "target_object": "can", "action_label": "pick_and_place", "summary": {"source_video_count": 1, "tracked_object_count": 3, "synthetic_output_count": len([s for s in syn_outputs if s["status"]=="succeeded"]), "duration_ms": dur}}
    pipeline_data = {"pipeline_id": "pipe_front_001", "run_id": "run_can_pickup_001", "label": "Front View", "status": "complete", "source_video": {"video_id": "video_front_001", "url": "/media/source.mp4", "filename": "source.mp4", "duration_ms": dur, "width": w, "height": h}, "detected_objects": [{"track_id": "hand_right_001", "label": "right_hand", "type": "actor_part", "color": "#35d0ff"}, {"track_id": "can_001", "label": "can", "type": "manipulated_object", "color": "#7cf29a"}, {"track_id": "table_001", "label": "table", "type": "support_surface", "color": "#5c5c6e"}], "stage_status": {"source_video": "complete", "detection": "complete", "tracking": "complete", "annotations": "complete", "world_model": "complete", "synthetic_outputs": "complete"}}
    tracks_data = [
        {"track_id": "hand_right_001", "pipeline_id": "pipe_front_001", "label": "right_hand", "type": "actor_part", "color": "#35d0ff", "frames": hand_frames},
        {"track_id": "can_001", "pipeline_id": "pipe_front_001", "label": "can", "type": "manipulated_object", "color": "#7cf29a", "frames": can_frames},
        {"track_id": "table_001", "pipeline_id": "pipe_front_001", "label": "table", "type": "support_surface", "color": "#5c5c6e", "frames": [{"t_ms": 0, "bbox": [0, table_y, w, table_h], "confidence": 0.98, "visible": True}, {"t_ms": dur, "bbox": [0, table_y, w, table_h], "confidence": 0.98, "visible": True}]},
    ]
    wm_data = {"world_model_id": "wm_pipe_front_001", "pipeline_id": "pipe_front_001", "target_object": "can", "action_label": "pick_and_place", "duration_ms": dur, "objects": [{"id": "hand_right_001", "label": "right_hand", "role": "actor"}, {"id": "can_001", "label": "can", "role": "manipulated_object"}, {"id": "table_001", "label": "table", "role": "support_surface"}], "actions": actions, "relations": relations}

    ann_code = """
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
        "// Auto-generated by full_regen pipeline - real data from BytePlus API",
        f"// Generated: {now}",
        "",
        f"export const run = {json.dumps(run_data, indent=2)};",
        "",
        f"export const pipeline = {json.dumps(pipeline_data, indent=2)};",
        "",
        f"export const tracks = {json.dumps(tracks_data, indent=2)};",
        "",
        f"export const worldModel = {json.dumps(wm_data, indent=2)};",
        "",
        f"export const syntheticOutputs = {json.dumps(syn_outputs, indent=2)};",
        ann_code,
    ]
    SEED_JS.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Seed JS written")

    # Also JSON
    with open(OUTPUT_DIR / "seed_data.json", "w") as f:
        json.dump({"run": run_data, "pipeline": pipeline_data, "tracks": tracks_data, "worldModel": wm_data, "syntheticOutputs": syn_outputs}, f, indent=2)
    print(f"  Seed JSON written")


def main():
    print("=" * 60)
    print("  Full Pipeline Regen")
    print("=" * 60)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Source video
    url = gen_source_video()
    if not url:
        print("FATAL: source video failed")
        sys.exit(1)
    src = OUTPUT_DIR / "source.mp4"
    download_video(url, src)
    shutil.copy2(src, MEDIA_DIR / "source.mp4")

    # Step 2: Detection
    hand_frames, can_frames, dur, w, h = run_detection(src)

    # Step 3: Action labels
    actions = label_actions(can_frames, dur)

    # Step 4: Synthetics (v2v via tunnel URL)
    source_public = f"{TUNNEL_BASE}/media/source.mp4"
    print(f"\n  Source video public URL: {source_public}")
    syn_results = gen_synthetics(source_public)

    # Download synthetic videos
    syn_files = {}
    for v in VARIATIONS:
        vurl = syn_results.get(v["id"], "")
        if vurl:
            fname = f"synthetic_{v['id']}.mp4"
            dest = OUTPUT_DIR / fname
            download_video(vurl, dest)
            shutil.copy2(dest, MEDIA_DIR / fname)
            syn_files[v["id"]] = fname

    # Step 5: Write seed data
    write_seed(hand_frames, can_frames, actions, dur, w, h, syn_results)

    succeeded = sum(1 for u in syn_results.values() if u)
    print(f"\n{'='*60}")
    print(f"  DONE - Source + {succeeded}/{len(VARIATIONS)} synthetics")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

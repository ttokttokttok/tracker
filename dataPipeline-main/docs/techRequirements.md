# PhysicalAI Dataset Studio - Technical Requirements

## Architecture

The app is split into two frontend routes and one backend API.

```text
Browser
  /record
    webcam
    overlay canvas
    MediaRecorder
    WebSocket client
    Seedance job status

  /dashboard
    run browser
    video comparison
    annotation timeline
    world-model viewer
    export controls

Backend
  FastAPI
  WebSocket frame/control channel
  detection pipeline
  recording storage
  world-model extraction
  Seedance job queue
  run database
```

## Recommended Stack

| Layer | Technology |
| --- | --- |
| Frontend | Vite plus React or Vite plus Vanilla JS |
| Styling | CSS modules or plain CSS with design tokens |
| Camera | `navigator.mediaDevices.getUserMedia` |
| Recording | `MediaRecorder` |
| Overlay | HTML canvas over video |
| Realtime channel | WebSocket |
| Backend | Python FastAPI |
| Detection | MVP: BytePlus Visual Grounding; target: enrollment plus local tracking |
| Generation | BytePlus Seedance 2 |
| Storage | Local filesystem for MVP; object storage later |
| Metadata | JSON files for MVP; SQLite/Postgres later |

## Route Responsibilities

### `/record`

The recording route owns live capture and new run creation.

Frontend responsibilities:

- Request camera permission.
- Show live video.
- Draw object bbox overlay.
- Start/stop recording.
- Send control events to backend.
- Upload recorded clip.
- Display current run status.
- Display Seedance job queue.

Backend responsibilities:

- Receive latest frames or snapshots.
- Run object detection/tracking.
- Emit bbox updates.
- Save uploaded clip.
- Build annotations.
- Build world model.
- Create Seedance jobs.
- Persist run metadata.

### `/dashboard`

The dashboard route owns run review and export.

Frontend responsibilities:

- Fetch run list.
- Fetch selected run details.
- Display source recording.
- Display generated variations.
- Draw annotations on video playback.
- Render action timeline.
- Render world-model JSON.
- Trigger export.

Backend responsibilities:

- List runs.
- Return run metadata.
- Serve source/generated videos.
- Serve annotations/world model.
- Return job statuses.
- Build export bundle.

## Backend API

### Runs

```http
GET /api/runs
GET /api/runs/{run_id}
GET /api/runs/{run_id}/world-model
GET /api/runs/{run_id}/annotations
GET /api/runs/{run_id}/variations
POST /api/runs/{run_id}/export
```

### Recording

```http
POST /api/recordings
POST /api/recordings/{run_id}/upload
POST /api/recordings/{run_id}/process
```

### Generation

```http
POST /api/runs/{run_id}/generate
GET /api/generation-jobs/{job_id}
```

### WebSocket

```text
WS /ws/record/{run_id}
```

Client messages:

```json
{
  "type": "start_tracking",
  "object_label": "cup"
}
```

```json
{
  "type": "frame_snapshot",
  "image_base64": "..."
}
```

```json
{
  "type": "start_recording"
}
```

```json
{
  "type": "stop_recording"
}
```

Server messages:

```json
{
  "type": "tracking_update",
  "bbox": [120, 280, 84, 92],
  "confidence": 0.92,
  "state": "tracking",
  "t_ms": 1200
}
```

```json
{
  "type": "generation_update",
  "variation_id": "warehouse",
  "status": "succeeded",
  "video_url": "/api/media/run_001/warehouse.mp4"
}
```

## Data Model

### Run

```json
{
  "run_id": "run_20260418_001",
  "created_at": "2026-04-18T15:00:00-07:00",
  "status": "complete",
  "target_object": "cup",
  "action_label": "pick_and_place",
  "source_video_url": "/api/media/run_20260418_001/clip_original.webm",
  "thumbnail_url": "/api/media/run_20260418_001/thumb.jpg",
  "world_model_url": "/api/runs/run_20260418_001/world-model",
  "annotations_url": "/api/runs/run_20260418_001/annotations",
  "variation_count": 5
}
```

### Annotation Frame

```json
{
  "frame_index": 42,
  "t_ms": 1400,
  "objects": [
    {
      "track_id": "object_001",
      "label": "cup",
      "bbox": [130, 220, 80, 80],
      "confidence": 0.91
    }
  ],
  "active_action_phase": "grasp"
}
```

### Variation

```json
{
  "variation_id": "warehouse",
  "run_id": "run_20260418_001",
  "status": "succeeded",
  "label": "Warehouse",
  "prompt": "Recreate the same action in an industrial warehouse...",
  "source_world_model_id": "run_20260418_001:world_model",
  "inherits_annotations": true,
  "video_url": "/api/media/run_20260418_001/warehouse.mp4",
  "created_at": "2026-04-18T15:06:00-07:00"
}
```

## Detection Strategy

Use two layers:

1. MVP detection: BytePlus Visual Grounding can find the object and return bbox updates.
2. Target detection: enrollment plus local reference tracking, with remote grounding used only for enrollment or recovery.

This avoids blocking the demo on local ML quality while keeping the architecture aligned with the stronger target design.

## Recording Pipeline

1. Browser starts webcam stream.
2. User starts tracking a target object.
3. Backend emits bbox updates.
4. User starts recording.
5. Browser records video with `MediaRecorder`.
6. Browser logs synchronized bbox updates.
7. User stops recording.
8. Browser uploads video blob.
9. Backend stores the clip.
10. Backend creates `annotations.json`.
11. Backend creates `world_model.json`.
12. Backend creates Seedance generation jobs.

## World-Model Extraction

The world model should be produced from:

- source video,
- target object label,
- bbox timeline,
- optional scene understanding from a vision model,
- action labeling from a multimodal model.

The world model is the canonical source of truth for dataset labels.

## Seedance 2 Integration

Seedance jobs must use the source video as `reference_video`.

Pseudo-code:

```python
def create_seedance_job(source_video_url: str, prompt: str):
    return client.content_generation.tasks.create(
        model="dreamina-seedance-2-0-260128",
        content=[
            {"type": "text", "text": prompt},
            {
                "type": "video_url",
                "video_url": {"url": source_video_url},
                "role": "reference_video"
            }
        ],
        generate_audio=False,
        ratio="16:9",
        duration=8,
        watermark=False
    )
```

Each prompt must explicitly preserve:

- same action,
- same object,
- same motion timing,
- same task outcome,
- same trajectory semantics.

## Frontend Design Requirements

The UI should feel polished and premium.

### Visual Direction

- Dark neutral workspace with crisp contrast.
- Large media-first layouts.
- Subtle depth through borders, shadows, and translucent panels.
- Sharp typography with strong hierarchy.
- Animated status transitions for recording, processing, and generation.
- Video thumbnails and waveform/timeline visuals.
- No plain table-only dashboard as the primary experience.

### `/record` UI Requirements

- Live video should dominate the page.
- Bbox overlay should be stable and readable.
- Recording status should be impossible to miss.
- Generation jobs should stream into the UI as cards.
- JSON/world-model panel should be available without taking over the main video.

### `/dashboard` UI Requirements

- Past runs should be easy to scan visually.
- The selected run should open into a rich review workspace.
- Original and generated videos should be easy to compare.
- The timeline should make action phases obvious.
- Raw JSON should be available for developers.

## Build Order

1. Create `/record` route with webcam preview.
2. Add bbox overlay rendering.
3. Add backend WebSocket for tracking updates.
4. Add MediaRecorder upload.
5. Store run metadata.
6. Generate annotations/world model.
7. Add Seedance job creation and polling.
8. Create `/dashboard` route with run list.
9. Add run detail view with source video.
10. Add annotation overlay playback.
11. Add generated variation gallery.
12. Add dataset export.

## MVP Success

- User can create a run from `/record`.
- User can record a video.
- User can see bbox annotations for the recording.
- User can generate at least one Seedance variation.
- User can open `/dashboard` and review the past run.
- User can export dataset metadata.


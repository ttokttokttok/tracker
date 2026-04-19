# Detection And Annotation Pipeline

## Purpose

The detection pipeline identifies and tracks the core object in the source recording. Its output becomes part of the annotation timeline and world model used by the dashboard and generated dataset.

The generated Seedance videos visually change the scene, but they are tied back to the same source annotation package.

## Two Detection Modes

The system supports an MVP mode and a target mode.

### MVP Mode: Remote Grounding Tracking

Use BytePlus Visual Grounding to find the target object and emit bbox updates.

This is acceptable for the first demo because it is simpler and faster to build.

Rules:

- Use one tracked object at a time.
- Poll grounding at a controlled interval, such as 300-500 ms.
- Smooth bbox movement on the frontend.
- Log every detection result.
- Mark low-confidence frames.

### Target Mode: Enrollment Plus Local Tracking

The target architecture uses an enrollment step before recording.

Flow:

1. User chooses target object.
2. System asks user to show the object from multiple angles.
3. System captures 3-5 high-quality reference crops.
4. Local tracker uses those references to re-identify the same object instance.
5. Remote grounding is used only for enrollment help or recovery.

This is stronger than per-frame remote grounding because it supports instance-level tracking and reduces API dependency.

## `/record` Detection Flow

```text
User opens /record
  -> camera starts
  -> user selects target object
  -> detection starts
  -> bbox overlay appears
  -> user starts recording
  -> video and bbox timeline are captured
  -> user stops recording
  -> annotation package is finalized
  -> world model is generated
  -> Seedance jobs are queued
```

## Pipeline Modules

### Frame Ingestion

Responsibilities:

- Receive live camera frames or snapshots.
- Keep latest frame for detection.
- Timestamp frames.
- Provide frame data to grounding/tracking modules.

Suggested interface:

```python
class FrameIngestion:
    def push_frame(self, frame_bytes: bytes, timestamp_ms: int) -> None: ...
    def get_latest_frame(self) -> bytes | None: ...
```

### Object Grounding

Responsibilities:

- Find target object in an image.
- Return bbox and confidence.
- Provide recovery when local tracking is lost.

Output:

```json
{
  "label": "cup",
  "bbox": [120, 280, 84, 92],
  "confidence": 0.92,
  "timestamp_ms": 1200,
  "provider": "byteplus_visual_grounding"
}
```

### Tracker

Responsibilities:

- Smooth bbox updates.
- Maintain object state.
- Mark tracking as `tracking`, `weak`, or `lost`.
- Emit stable bbox output to the frontend and recording logger.

Suggested states:

| State | Meaning |
| --- | --- |
| `tracking` | Confident bbox is available. |
| `weak` | Object may be visible but confidence is low. |
| `lost` | Object cannot be reliably tracked. |

### Annotation Recorder

Responsibilities:

- Record bbox updates during source video capture.
- Align bbox frames to video timestamps.
- Store confidence and tracking state.
- Produce `annotations.json`.

Annotation record:

```json
{
  "frame_index": 42,
  "t_ms": 1400,
  "track_id": "object_001",
  "label": "cup",
  "bbox": [130, 220, 80, 80],
  "confidence": 0.91,
  "tracking_state": "tracking"
}
```

### World-Model Builder

Responsibilities:

- Convert raw tracking data and video analysis into structured task data.
- Identify action phases.
- Identify visible scene objects.
- Identify spatial relations.
- Persist `world_model.json`.

Inputs:

- source video,
- target object,
- bbox timeline,
- optional vision-model scene analysis.

Output:

```json
{
  "run_id": "run_20260418_001",
  "target_object": "cup",
  "action_label": "pick_and_place",
  "duration_ms": 4200,
  "actions": [
    {
      "phase": "reach",
      "t_start_ms": 600,
      "t_end_ms": 1200
    }
  ],
  "scene": {
    "objects": ["cup", "hand", "table"],
    "relations": [
      {
        "subject": "cup",
        "relation": "on_top_of",
        "object": "table"
      }
    ]
  }
}
```

### Generation Constraint Builder

Responsibilities:

- Convert the world model into prompt constraints for Seedance.
- Ensure every variation preserves the source action.
- Store prompts for dashboard review.

Prompt template:

```text
Reference Video 1 shows a person performing this action:
{action_summary}

Recreate the same action in this new scene:
{scene_variation}

Hard constraints:
- preserve the same target object: {target_object}
- preserve the same action phase order
- preserve the same approximate timing
- preserve the same task outcome
- preserve the same object trajectory semantics
```

## Logging Events

Minimum events:

- `run_created`
- `camera_ready`
- `tracking_requested`
- `object_grounded`
- `tracking_started`
- `tracking_update`
- `tracking_weak`
- `tracking_lost`
- `recording_started`
- `recording_stopped`
- `clip_uploaded`
- `annotations_created`
- `world_model_created`
- `generation_jobs_created`
- `generation_job_updated`
- `run_completed`

Example:

```json
{
  "run_id": "run_20260418_001",
  "event": "tracking_update",
  "t_ms": 1400,
  "data": {
    "bbox": [130, 220, 80, 80],
    "confidence": 0.91,
    "state": "tracking"
  }
}
```

## Dashboard Requirements For Detection Data

The dashboard must be able to replay detection data against the source video.

Required features:

- draw bbox overlay while source video plays,
- show active action phase at current timestamp,
- show confidence over time,
- show weak/lost tracking segments,
- jump from timeline event to video timestamp,
- display raw annotation JSON.

## Quality Checks

Before a run is marked complete:

- Source video exists.
- Target object label exists.
- At least one valid track exists.
- Bbox timeline covers most of the recording.
- World model has action phases.
- Seedance jobs reference the source video.
- Generated variations are linked to the parent run id.


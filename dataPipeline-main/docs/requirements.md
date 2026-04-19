# PhysicalAI Dataset Studio - Product Requirements

## Product Goal

PhysicalAI Dataset Studio turns one recorded human demonstration into a reusable training-data package.

The app records a real video of a person performing an action, extracts the core objects and action timeline into a world model, and then uses Seedance 2 to generate scene variations that preserve the same task structure.

## Core Product Shape

The product has two primary URLs:

| URL | Name | Purpose |
| --- | --- | --- |
| `/record` | Recording Studio | Capture a new action demo, track the target object, extract annotations, and launch Seedance generation. |
| `/dashboard` | Run Dashboard | Review past runs, inspect source videos, view annotations/world models, watch generated variations, and export datasets. |

## Primary User Flow

1. User opens `/record`.
2. User selects or speaks the target object, such as `cup`, `bottle`, `laptop`, or `box`.
3. System detects and tracks the target object.
4. User starts recording.
5. User performs an action, such as pick up, move, place, open, close, push, or stack.
6. User stops recording.
7. System saves the original video.
8. System extracts annotations:
   - object bounding boxes,
   - action phases,
   - scene objects,
   - spatial relations,
   - world-model metadata.
9. System sends the source video and world-model constraints to Seedance 2.
10. Seedance generates multiple videos in different scenes.
11. User opens `/dashboard` to review the run and generated variations.
12. User exports the complete dataset package.

## What Must Stay The Same In Generated Videos

Every generated variation must preserve the source run's core task data.

### Required Invariants

- Same source action.
- Same target object category.
- Same action phase order.
- Same approximate action timing.
- Same object trajectory semantics.
- Same task outcome.
- Same annotation schema.
- Same parent run id.

### Allowed Changes

- Background scene.
- Lighting.
- Surface material.
- Camera style, when requested.
- Actor embodiment, such as human hand to robot gripper.
- Visual style, if it does not break the task.

### Not Allowed

- Changing the action sequence.
- Changing the manipulated object into an unrelated object unless the variation explicitly asks for object substitution.
- Changing the task outcome.
- Dropping the manipulated object from the generated video.
- Producing videos that cannot be mapped back to the original world model.

## Module 1: `/record` Recording Studio

The recording module is the live capture experience.

### Responsibilities

- Show live webcam feed.
- Accept voice or typed target-object command.
- Track one target object.
- Render bounding-box overlay.
- Record the source video.
- Capture tracking data while recording.
- Extract or request action/world-model annotations.
- Start Seedance generation jobs.
- Show generation progress for the current run.

### Recording Studio Layout

The UI should feel like a high-end creative tool, not a plain admin form.

Recommended layout:

- Large full-bleed video work area.
- Live object overlay with bbox, label, and confidence.
- Compact command dock for tracking and recording controls.
- Timeline strip under the video.
- Right-side generation queue with Seedance job cards.
- Bottom world-model drawer that can expand into structured JSON.

### Recording States

| State | Description |
| --- | --- |
| `idle` | Camera is ready, no target selected. |
| `detecting` | System is finding the target object. |
| `tracking` | Target object is locked and bbox overlay is active. |
| `recording` | Source video and per-frame annotations are being captured. |
| `processing` | Video is saved and annotations are being generated. |
| `generating` | Seedance jobs are queued or running. |
| `complete` | Source run and generated variations are available. |
| `error` | A recoverable failure occurred. |

## Module 2: `/dashboard` Run Dashboard

The dashboard module is the review, comparison, and export experience.

### Responsibilities

- List past runs.
- Show each source recording.
- Show generated Seedance variations.
- Display annotation timelines.
- Display world-model JSON.
- Compare original video with generated scenes.
- Show job status and failure reasons.
- Export dataset packages.

### Dashboard Layout

Recommended layout:

- Left sidebar: run list with search, object filter, status filter, and date filter.
- Main top area: selected source video and generated video comparison.
- Main middle area: action timeline with phase markers.
- Main lower area: tabs for annotations, world model, generation prompts, logs, and export manifest.
- Right rail: variation cards with status, scene label, duration, and quality notes.

### Past Run Card

Each run card should include:

- thumbnail from source video,
- run id,
- target object,
- action label,
- created timestamp,
- generation status,
- number of variations,
- export status.

## World Model

The world model is the canonical structured output from the real recording.

Generated videos do not create a new independent world model by default. They inherit the parent run's world model and add variation metadata.

### Source World Model Example

```json
{
  "run_id": "run_20260418_001",
  "source_video": "clip_original.webm",
  "target_object": {
    "label": "cup",
    "track_id": "object_001"
  },
  "duration_ms": 4200,
  "scene": {
    "objects": ["cup", "hand", "table", "laptop"],
    "relations": [
      {
        "subject": "cup",
        "relation": "on_top_of",
        "object": "table"
      },
      {
        "subject": "cup",
        "relation": "left_of",
        "object": "laptop"
      }
    ]
  },
  "actions": [
    {
      "phase": "idle",
      "t_start_ms": 0,
      "t_end_ms": 600
    },
    {
      "phase": "reach",
      "t_start_ms": 600,
      "t_end_ms": 1200
    },
    {
      "phase": "grasp",
      "t_start_ms": 1200,
      "t_end_ms": 1700
    },
    {
      "phase": "lift_and_move",
      "t_start_ms": 1700,
      "t_end_ms": 3200
    },
    {
      "phase": "place",
      "t_start_ms": 3200,
      "t_end_ms": 4200
    }
  ],
  "tracks": [
    {
      "track_id": "object_001",
      "label": "cup",
      "frames": [
        {
          "t_ms": 0,
          "bbox": [120, 280, 84, 92],
          "confidence": 0.92
        }
      ]
    }
  ]
}
```

## Seedance 2 Generation

Seedance must use the recorded source video as the reference input. A still image or object crop is not enough for this product because the generated video needs to preserve the motion arc.

### Generation Inputs

- Source video URL.
- Target object label.
- World model summary.
- Action phase timing.
- Scene variation prompt.

### Variation Examples

| Variation | Goal |
| --- | --- |
| Warehouse | Same action in an industrial workspace. |
| Night Desk | Same action under low light and desk-lamp shadows. |
| Outdoor Table | Same action outside on a wooden surface. |
| Robot Gripper | Replace the human hand with a robot gripper while preserving task timing. |
| Clean Lab | Same action in a clean robotics lab environment. |

## Dataset Export

Each completed run should export a folder or zip with:

```text
run_20260418_001/
  clip_original.webm
  world_model.json
  annotations.json
  generation_jobs.json
  variations/
    warehouse.mp4
    night_desk.mp4
    outdoor_table.mp4
    robot_gripper.mp4
    clean_lab.mp4
  dataset_manifest.json
```

## Success Criteria

- `/record` can capture a source demo video.
- The target object can be detected and tracked during recording.
- The app saves per-frame bbox annotations.
- The app creates a source world model.
- Seedance 2 receives the source video as `reference_video`.
- Generated variations appear as jobs complete.
- `/dashboard` shows past runs.
- `/dashboard` can replay source video with annotations.
- `/dashboard` can show generated variations next to the original.
- Dataset export includes source video, annotations, world model, generated videos, and manifest.


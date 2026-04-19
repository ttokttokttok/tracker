# PhysicalAI Dataset Studio - Project Submission Discussion

## Project Summary

PhysicalAI Dataset Studio is a dashboard-driven system for turning a small number of human demonstration videos into structured robot-training data.

The user records or uploads a source video of a physical action, such as picking up a can, moving a cup, or placing an object on a table. The system detects the important objects in the video, tracks the manipulated object and hands over time, generates annotation data and a world model, and then uses Seedance 2 to create synthetic video variations in different scenes.

The final result is not just a generated video. It is a dataset package containing:

- source video,
- object and hand tracks,
- action phase annotations,
- world-model JSON,
- generated synthetic variations,
- generation prompts and metadata,
- export manifest.

## Problem

Robotics and Physical AI systems need large amounts of task-specific training data. Capturing this data manually is slow, expensive, and difficult to scale because each new scene, lighting condition, camera angle, or environment usually requires another real-world recording.

A single human demonstration contains valuable information:

- what object is manipulated,
- how the hand approaches the object,
- when contact happens,
- how the object moves,
- where the object is placed,
- what the surrounding scene contains.

However, raw video alone is not enough. To become useful training data, the video needs structured annotations and variations.

PhysicalAI Dataset Studio addresses this by converting one source demonstration into a structured source pipeline, then generating synthetic variations that preserve the same task semantics.

## Core Idea

The core idea is:

```text
one real source video
  -> detected objects and tracks
  -> action/world-model annotations
  -> Seedance scene variations
  -> exportable training dataset
```

The generated videos are connected to the original source data. They are not treated as unrelated creative outputs. Each synthetic video inherits the source pipeline's world model and records which source video, prompt, and constraints produced it.

## Product Structure

The product has two main areas.

### Recording Studio: `/record`

The recording module is used to create new source demonstrations.

Users can:

- open the webcam,
- select or speak the target object,
- see object tracking overlays,
- record an action,
- stop recording,
- start annotation and generation.

### Run Dashboard: `/dashboard`

The dashboard is the main review and data-generation workspace.

Users can:

- browse past runs,
- open a run,
- review one or two source videos,
- play videos with synced tracking overlays,
- inspect detected objects, hands, and manipulated objects,
- view annotation data and world-model JSON,
- review Seedance-generated synthetic videos,
- compare source and synthetic outputs,
- export the full dataset package.

## Source Video Pipeline

Each source video has its own data-generation pipeline.

```text
Source Video
  -> Detection
  -> Tracking
  -> Annotations
  -> World Model
  -> Synthetic Outputs
```

This design matters because a run may include multiple views of the same action, such as a front camera and a side camera. Each video has different pixel coordinates and therefore needs its own tracking and annotation data.

At the same time, the videos can share the same high-level action meaning: the user picked up a can, moved it, and placed it on the table.

## What The Dashboard Shows

For each source pipeline, the dashboard shows:

- the original source video,
- overlays for tracked objects such as `right_hand` and `can`,
- bounding boxes synchronized with playback,
- current action phase,
- confidence and tracking state,
- detected object list,
- action timeline,
- scene relations,
- world-model JSON,
- generated synthetic video outputs.

Example annotation at a timestamp:

```json
{
  "t_ms": 1400,
  "active_action_phase": "grasp",
  "objects": [
    {
      "track_id": "hand_right_001",
      "label": "right_hand",
      "bbox": [430, 245, 160, 190],
      "confidence": 0.89
    },
    {
      "track_id": "can_001",
      "label": "can",
      "bbox": [610, 330, 88, 150],
      "confidence": 0.94
    }
  ],
  "relations": [
    {
      "subject": "right_hand",
      "relation": "touching",
      "object": "can"
    }
  ]
}
```

## World Model

The world model is the structured representation of what happened in the source video.

It includes:

- target object,
- actor parts such as hands,
- support surfaces such as tables,
- visible scene objects,
- action phases,
- object tracks,
- spatial and temporal relations.

Example action phases:

```json
[
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
    "t_end_ms": 3300
  },
  {
    "phase": "place",
    "t_start_ms": 3300,
    "t_end_ms": 4200
  }
]
```

## Seedance 2 Usage

Seedance 2 is used to generate synthetic videos from the source demonstration.

The important design decision is that the source video is used as the reference input. This preserves the motion arc better than using a single still image or object crop.

Each generation prompt includes hard constraints:

- preserve the same target object,
- preserve the same action phase order,
- preserve the same approximate timing,
- preserve the same task outcome,
- preserve the same trajectory semantics.

Only the scene or visual embodiment changes.

Example variations:

- same action in an industrial warehouse,
- same action on an outdoor table,
- same action under night desk lighting,
- same action in a clean robotics lab,
- same action with a robot gripper replacing the human hand.

## Why This Is Useful

This project turns one real demonstration into multiple labeled training examples.

For example:

```text
1 recorded can pickup
  -> 1 source video
  -> 1 annotation/world-model package
  -> 5 synthetic scene variations
  -> 6 total dataset samples
```

The synthetic samples are valuable because they increase scene diversity while keeping the task structure consistent.

This can help Physical AI teams test models against variations in:

- lighting,
- backgrounds,
- surfaces,
- camera perspectives,
- actor embodiment,
- environmental clutter.

## Technical Approach

### Frontend

- `/record` for capture.
- `/dashboard` for review.
- Video playback with overlay rendering.
- Timeline and action phase visualization.
- Source/synthetic comparison.
- JSON and metadata inspection.

### Backend

- FastAPI service.
- Run and source-pipeline storage.
- Video upload and serving.
- Detection/tracking pipeline.
- Annotation generation.
- World-model creation.
- Seedance job creation and polling.
- Dataset export.

### Detection

The MVP can use remote visual grounding for object detection and bbox updates.

The target design supports enrollment-based local tracking:

1. User shows the object.
2. System captures multiple reference crops.
3. Local tracking identifies the same object instance.
4. Remote grounding is used only for recovery.

This gives the project a practical demo path while preserving a stronger long-term architecture.

## Dataset Export

Each completed run can export:

```text
run_can_pickup_001/
  source/
    front.webm
    side.webm
  annotations/
    annotations_pipe_front_001.json
    annotations_pipe_side_001.json
  world_models/
    world_model_pipe_front_001.json
    world_model_pipe_side_001.json
  synthetic/
    warehouse.mp4
    night_desk.mp4
    outdoor_table.mp4
    robot_gripper.mp4
  prompts/
    generation_prompts.json
  dataset_manifest.json
```

## Demo Walkthrough

1. Open the dashboard.
2. Select a past run called `Can pickup demo`.
3. Play the source video.
4. Show overlays tracking the hand and can as the video plays.
5. Open the annotation timeline and show action phases.
6. Open the world-model panel and show structured JSON.
7. Open the synthetic data panel.
8. Play generated Seedance variations.
9. Compare the original and generated video side by side.
10. Export the complete dataset package.

## Judging Pitch

PhysicalAI Dataset Studio compresses the workflow from demonstration capture to synthetic dataset generation.

Instead of treating video generation as a visual gimmick, the project ties generated videos back to structured source annotations. The source video is converted into a data-generation pipeline, and every synthetic output remains linked to the source video, object tracks, action phases, world model, prompt, and constraints.

The result is a practical tool for creating Physical AI training data from small numbers of real human demonstrations.

## Current Scope

MVP:

- one dashboard,
- one or two source videos per run,
- hand and object overlays,
- annotation timeline,
- world-model JSON,
- Seedance output gallery,
- dataset export manifest.

Future:

- manual annotation correction,
- segmentation masks,
- local reference-based tracking,
- multi-camera synchronization,
- quality scoring for generated videos,
- direct training-data export formats for robotics pipelines.


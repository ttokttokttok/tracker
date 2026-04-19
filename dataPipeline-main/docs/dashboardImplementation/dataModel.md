# Dashboard Data Model

## Core Entity Relationship

```text
Run
  has many SourcePipelines

SourcePipeline
  has one SourceVideo
  has many ObjectTracks
  has many AnnotationFrames
  has one WorldModel
  has many SyntheticOutputs
```

## Run

```json
{
  "run_id": "run_can_pickup_001",
  "name": "Can pickup demo",
  "created_at": "2026-04-18T15:30:00-07:00",
  "status": "complete",
  "target_object": "can",
  "action_label": "pick_and_place",
  "thumbnail_url": "/media/run_can_pickup_001/thumb.jpg",
  "source_pipeline_ids": ["pipe_front_001", "pipe_side_001"],
  "summary": {
    "source_video_count": 2,
    "tracked_object_count": 3,
    "synthetic_output_count": 5,
    "duration_ms": 4200
  }
}
```

## SourcePipeline

```json
{
  "pipeline_id": "pipe_front_001",
  "run_id": "run_can_pickup_001",
  "label": "Front view",
  "status": "complete",
  "source_video": {
    "video_id": "video_front_001",
    "url": "/media/run_can_pickup_001/front.webm",
    "filename": "front.webm",
    "duration_ms": 4200,
    "width": 1280,
    "height": 720
  },
  "detected_objects": [
    {
      "track_id": "hand_right_001",
      "label": "right_hand",
      "type": "actor_part",
      "color": "#35d0ff"
    },
    {
      "track_id": "can_001",
      "label": "can",
      "type": "manipulated_object",
      "color": "#7cf29a"
    }
  ],
  "stage_status": {
    "source_video": "complete",
    "detection": "complete",
    "tracking": "complete",
    "annotations": "complete",
    "world_model": "complete",
    "synthetic_outputs": "complete"
  }
}
```

## ObjectTrack

```json
{
  "track_id": "can_001",
  "pipeline_id": "pipe_front_001",
  "label": "can",
  "type": "manipulated_object",
  "frames": [
    {
      "t_ms": 0,
      "bbox": [610, 330, 88, 150],
      "confidence": 0.94,
      "visible": true
    },
    {
      "t_ms": 500,
      "bbox": [612, 328, 90, 152],
      "confidence": 0.95,
      "visible": true
    }
  ]
}
```

## AnnotationFrame

```json
{
  "pipeline_id": "pipe_front_001",
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

## WorldModel

```json
{
  "world_model_id": "wm_pipe_front_001",
  "pipeline_id": "pipe_front_001",
  "target_object": "can",
  "action_label": "pick_and_place",
  "duration_ms": 4200,
  "objects": [
    {
      "id": "hand_right_001",
      "label": "right_hand",
      "role": "actor"
    },
    {
      "id": "can_001",
      "label": "can",
      "role": "manipulated_object"
    },
    {
      "id": "table_001",
      "label": "table",
      "role": "support_surface"
    }
  ],
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
      "t_end_ms": 3300
    },
    {
      "phase": "place",
      "t_start_ms": 3300,
      "t_end_ms": 4200
    }
  ],
  "relations": [
    {
      "subject": "can",
      "relation": "on_top_of",
      "object": "table",
      "t_start_ms": 0,
      "t_end_ms": 1200
    },
    {
      "subject": "right_hand",
      "relation": "holding",
      "object": "can",
      "t_start_ms": 1700,
      "t_end_ms": 3300
    }
  ]
}
```

## SyntheticOutput

```json
{
  "synthetic_id": "synth_warehouse_001",
  "pipeline_id": "pipe_front_001",
  "run_id": "run_can_pickup_001",
  "label": "Warehouse",
  "status": "succeeded",
  "provider": "seedance_2",
  "source_video_id": "video_front_001",
  "source_world_model_id": "wm_pipe_front_001",
  "inherits_annotations": true,
  "prompt": "Reference Video 1 shows a person picking up a can...",
  "constraints": [
    "preserve same target object: can",
    "preserve same action phase order",
    "preserve same approximate timing",
    "preserve same task outcome"
  ],
  "video_url": "/media/run_can_pickup_001/synthetic/warehouse.mp4",
  "created_at": "2026-04-18T15:38:00-07:00"
}
```

## DatasetManifest

```json
{
  "run_id": "run_can_pickup_001",
  "exported_at": "2026-04-18T15:45:00-07:00",
  "source_pipelines": [
    {
      "pipeline_id": "pipe_front_001",
      "source_video": "front.webm",
      "annotations": "annotations_pipe_front_001.json",
      "world_model": "world_model_pipe_front_001.json",
      "synthetic_outputs": [
        "warehouse.mp4",
        "night_desk.mp4"
      ]
    }
  ]
}
```


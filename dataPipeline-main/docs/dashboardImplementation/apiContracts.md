# Dashboard API Contracts

## Runs

### List Runs

```http
GET /api/runs
```

Response:

```json
{
  "runs": [
    {
      "run_id": "run_can_pickup_001",
      "name": "Can pickup demo",
      "status": "complete",
      "target_object": "can",
      "action_label": "pick_and_place",
      "thumbnail_url": "/media/run_can_pickup_001/thumb.jpg",
      "created_at": "2026-04-18T15:30:00-07:00",
      "source_video_count": 2,
      "synthetic_output_count": 5
    }
  ]
}
```

### Get Run Detail

```http
GET /api/runs/{run_id}
```

Response:

```json
{
  "run": {},
  "source_pipelines": [],
  "synthetic_summary": {
    "queued": 0,
    "running": 1,
    "succeeded": 4,
    "failed": 0
  }
}
```

## Source Pipelines

### Get Source Pipeline

```http
GET /api/runs/{run_id}/pipelines/{pipeline_id}
```

Response:

```json
{
  "pipeline": {},
  "detected_objects": [],
  "stage_status": {}
}
```

### Add Source Video To Run

```http
POST /api/runs/{run_id}/pipelines
Content-Type: multipart/form-data
```

Form fields:

- `video`: file.
- `label`: source video label.
- `target_object`: optional object label.

Response:

```json
{
  "pipeline_id": "pipe_front_001",
  "status": "uploaded"
}
```

### Reprocess Source Pipeline

```http
POST /api/runs/{run_id}/pipelines/{pipeline_id}/process
```

Body:

```json
{
  "target_objects": ["right_hand", "can"],
  "generate_world_model": true
}
```

Response:

```json
{
  "pipeline_id": "pipe_front_001",
  "status": "processing"
}
```

## Annotations

### Get Tracks

```http
GET /api/runs/{run_id}/pipelines/{pipeline_id}/tracks
```

Response:

```json
{
  "tracks": []
}
```

### Get Annotation Frames

```http
GET /api/runs/{run_id}/pipelines/{pipeline_id}/annotations
```

Query params:

- `start_ms`
- `end_ms`
- `sample_rate`

Response:

```json
{
  "pipeline_id": "pipe_front_001",
  "frames": []
}
```

### Get Annotation At Timestamp

```http
GET /api/runs/{run_id}/pipelines/{pipeline_id}/annotations/current?t_ms=1400
```

Response:

```json
{
  "t_ms": 1400,
  "active_action_phase": "grasp",
  "objects": [],
  "relations": []
}
```

## World Model

### Get Pipeline World Model

```http
GET /api/runs/{run_id}/pipelines/{pipeline_id}/world-model
```

Response:

```json
{
  "world_model": {}
}
```

## Synthetic Outputs

### List Synthetic Outputs

```http
GET /api/runs/{run_id}/pipelines/{pipeline_id}/synthetic-outputs
```

Response:

```json
{
  "outputs": []
}
```

### Generate Synthetic Outputs

```http
POST /api/runs/{run_id}/pipelines/{pipeline_id}/generate
```

Body:

```json
{
  "variations": [
    {
      "id": "warehouse",
      "label": "Warehouse",
      "scene_prompt": "industrial warehouse with concrete floor and metal shelving"
    }
  ]
}
```

Response:

```json
{
  "jobs": [
    {
      "job_id": "job_001",
      "synthetic_id": "synth_warehouse_001",
      "status": "queued"
    }
  ]
}
```

### Get Generation Job

```http
GET /api/generation-jobs/{job_id}
```

Response:

```json
{
  "job_id": "job_001",
  "status": "running",
  "progress": 0.45,
  "synthetic_id": "synth_warehouse_001"
}
```

## Export

### Export Run

```http
POST /api/runs/{run_id}/export
```

Body:

```json
{
  "include_source_videos": true,
  "include_annotations": true,
  "include_world_models": true,
  "include_synthetic_outputs": true
}
```

Response:

```json
{
  "export_id": "export_001",
  "status": "building"
}
```


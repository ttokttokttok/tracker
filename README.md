# PhysicalAI Dataset Studio

Turn one recorded human demonstration into a reusable robot-training dataset. The pipeline records a real action video, tracks the target object, extracts a structured world model, and uses Seedance to generate scene variations that preserve the same task structure.

## What it does

1. **Record** — capture a demo video via webcam with live object tracking and bounding-box overlay
2. **Annotate** — extract per-frame bbox detections, action phases, and a structured world model
3. **Generate** — send the source video to Seedance and produce synthetic scene variations (warehouse, kitchen, outdoor, etc.)
4. **Review** — browse past runs, compare source vs. generated videos, inspect annotations
5. **Export** — download a complete dataset package (source video + annotations + world model + generated videos)

## Folder structure

```
dataPipeline-main/
  pipeline/          # Python data pipeline (E2E seed data generation)
  backend/           # Butterbase schema and push scripts
  dashboard/         # React/Vite review dashboard
  docs/              # Product and technical specs
```

## Stack

| Layer | Technology |
|---|---|
| Frontend | Vite + React |
| Backend / DB | Butterbase (managed Postgres + REST API) |
| Detection | BytePlus Visual Grounding (`seed-2-0-pro`) |
| Action labeling | BytePlus LLM (`seed-2-0-lite`) |
| Video generation | BytePlus Seedance (`seedance-1-5-pro`, `seedance-2-0`) |

## Pipeline quickstart

```bash
cd pipeline
pip install -r requirements.txt
```

Create a `.env` file:

```
ARK_API_KEY=your_byteplus_ark_api_key
```

Run the full end-to-end pipeline:

```bash
python e2e_pipeline.py
```

This generates a source video, runs object detection on each frame, labels action phases, builds the world model, submits three Seedance variation jobs, and writes `output/seed_data.json` plus copies all videos to `dashboard/public/media/`.

Other pipeline scripts:

| Script | Purpose |
|---|---|
| `full_regen.py` | Regenerate all seed data from scratch |
| `regen_matched.py` | Regenerate only matched/confirmed tracks |
| `regen_synthetic.py` | Re-submit Seedance generation jobs |
| `resume_synthetic.py` | Resume polling for in-flight Seedance jobs |

## Dashboard quickstart

```bash
cd dashboard
npm install
npm run dev
```

Open `http://localhost:5173` to browse runs, replay annotated source videos, and watch generated variations.

## Backend / Butterbase

The backend uses [Butterbase](https://butterbase.ai) — a managed Postgres + REST API service. Schema lives in `backend/butterbase_schema.json`.

```bash
# Push schema and seed data to Butterbase
BUTTERBASE_APP_ID=your_app_id bash backend/push_to_butterbase.sh
```

Set `BUTTERBASE_APP_ID` in your environment or `.env`.

## Docs

| File | Contents |
|---|---|
| `docs/requirements.md` | Full product requirements |
| `docs/techRequirements.md` | Technical architecture and API spec |
| `docs/infrastructure.md` | Butterbase + ionroute setup |
| `docs/detectionSetup.md` | Object detection configuration |
| `docs/dashboardImplementation/` | Dashboard module specs |

## World model format

Every run produces a `world_model.json` with objects, action phases, and spatial relations:

```json
{
  "target_object": "can",
  "action_label": "pick_and_place",
  "duration_ms": 5000,
  "objects": [...],
  "actions": [
    {"phase": "idle", "t_start_ms": 0, "t_end_ms": 600},
    {"phase": "reach", "t_start_ms": 600, "t_end_ms": 1200},
    {"phase": "grasp", "t_start_ms": 1200, "t_end_ms": 1700},
    {"phase": "lift_and_move", "t_start_ms": 1700, "t_end_ms": 3200},
    {"phase": "place", "t_start_ms": 3200, "t_end_ms": 5000}
  ],
  "relations": [...]
}
```

Generated variations inherit the parent world model — the scene changes, the task structure does not.

## Dataset export structure

```
run_20260418_001/
  clip_original.webm
  world_model.json
  annotations.json
  generation_jobs.json
  variations/
    warehouse.mp4
    kitchen.mp4
    outdoor.mp4
  dataset_manifest.json
```

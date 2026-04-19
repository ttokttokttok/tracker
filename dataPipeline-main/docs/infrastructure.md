# Infrastructure

## Backend — Butterbase

We use [Butterbase](https://butterbase.ai) as our Backend-as-a-Service. It provides a managed PostgreSQL database, REST API, file storage, and authentication — no custom backend server needed.

### Why Butterbase

- Instant PostgreSQL database with JSONB support (critical for storing per-frame detection data and world models)
- Auto-generated REST API with filtering, sorting, pagination
- Built-in file storage via presigned URLs (for video assets)
- JWT authentication out of the box
- Designed for AI-assisted development workflows

### App Details

- **App ID**: set `BUTTERBASE_APP_ID` locally
- **API Base**: `https://api.butterbase.ai/v1/$BUTTERBASE_APP_ID`
- **Dashboard subdomain**: set per deployment

### Database Schema

| Table | Purpose | Key Columns |
|---|---|---|
| `runs` | Run metadata | name, status, target_object, action_label, duration_ms |
| `pipelines` | Source video + detection info | run_id, video_url, detected_objects (jsonb), stage_status (jsonb) |
| `tracks` | Per-frame bbox tracking data | pipeline_id, label, track_type, color, frames (jsonb) |
| `world_models` | Scene understanding | pipeline_id, objects (jsonb), actions (jsonb), relations (jsonb) |
| `synthetic_outputs` | Generated video metadata | pipeline_id, run_id, label, status, prompt, video_url |

### API Examples

```bash
# List all runs
curl https://api.butterbase.ai/v1/$BUTTERBASE_APP_ID/runs \
  -H "Authorization: Bearer bb_sk_..."

# Get tracks for a pipeline
curl "https://api.butterbase.ai/v1/$BUTTERBASE_APP_ID/tracks?pipeline_id=eq.<pipeline_id>" \
  -H "Authorization: Bearer bb_sk_..."

# Get synthetic outputs for a run
curl "https://api.butterbase.ai/v1/$BUTTERBASE_APP_ID/synthetic_outputs?run_id=eq.<run_id>" \
  -H "Authorization: Bearer bb_sk_..."
```

### MCP Integration

Butterbase can be added as an MCP server for AI-assisted development:

```bash
claude mcp add butterbase https://api.butterbase.ai/mcp \
  --transport http --scope user \
  --header "Authorization: Bearer bb_sk_..."
```

---

## LLM Inference — ionroute.io

We use [ionroute.io](https://ionroute.io) for LLM inference routing. ionroute provides an OpenAI-compatible API gateway that routes requests to the best available model based on cost, latency, and capability.

### Why ionroute

- OpenAI-compatible API — drop-in replacement, no code changes
- Smart routing across multiple LLM providers
- Cost optimization — automatically picks the cheapest model that meets quality requirements
- Fallback handling — if one provider is down, requests route to another
- Usage tracking and analytics

### Usage in the Pipeline

The data pipeline uses LLM inference for:
1. **Action labeling** — classifying trajectory data into action phases (idle, reach, grasp, lift, place)
2. **Intent parsing** — parsing voice commands into structured JSON
3. **Scene understanding** — generating world model descriptions from detection data

### Integration

ionroute exposes an OpenAI-compatible endpoint. Point your OpenAI SDK client at ionroute:

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.ionroute.io/v1",
    api_key="your_ionroute_key",
)

response = client.chat.completions.create(
    model="auto",  # ionroute picks the best model
    messages=[{"role": "user", "content": "Label these action phases..."}],
)
```

### Current Pipeline Models

For the hackathon, we use BytePlus models directly:
- **seed-2-0-lite-260228** — text LLM for action labeling and intent parsing
- **seed-2-0-pro-260328** — vision model for object detection
- **seedance-1-5-pro-251215** — video generation (text-to-video)
- **dreamina-seedance-2-0-260128** — video generation (video-to-video with reference)

Post-hackathon, these can be routed through ionroute for better cost/latency optimization.

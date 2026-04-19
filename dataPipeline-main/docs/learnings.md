# API & Seedance Learnings

Hard-won findings from e2e testing on 2026-04-18. Read this before writing any BytePlus integration code.

---

## SDK Setup

```bash
pip install byteplus-python-sdk-v2
```

```python
from byteplussdkarkruntime import Ark

client = Ark(
    base_url="https://ark.ap-southeast.bytepluses.com/api/v3",
    api_key=os.getenv("ARK_API_KEY"),
)
```

- The SDK package name is `byteplus-python-sdk-v2` but the import is `byteplussdkarkruntime`.
- Store the API key in `.env`, never commit it. The hackathon key is shared and will be revoked if leaked.

---

## Response Format — Responses API

The `client.responses.create()` method returns a structured object, NOT plain text.

```python
response = client.responses.create(model="seed-2-0-lite-260228", input="Hello")
```

The response has an `.output` field which is a **list of `ResponseReasoningItem` objects**, not a string. To extract the actual text:

```python
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
```

**Do not** call `str(response)` and try to parse it. Use the helper above.

---

## Models That Work

Tested and confirmed working with the hackathon API key:

| Model ID | Use Case | Latency | Notes |
|---|---|---|---|
| `seed-2-0-lite-260228` | Text LLM (intent parsing, action labeling) | ~2-4s | Fast, reliable, follows JSON instructions well |
| `seed-2-0-pro-260328` | Vision understanding + visual grounding | ~3-6s | Handles base64 images, returns bbox coordinates |
| `seedance-1-5-pro-251215` | Video generation | ~60-120s | **This is the one that actually works.** |

### Models that DO NOT work reliably

| Model ID | Issue |
|---|---|
| `dreamina-seedance-2-0-260128` | Tasks stay `queued` indefinitely. The hackathon queue is completely backed up (3000+ tasks). |
| `dreamina-seedance-2-0-fast-260128` | Same issue — queued forever. |

**Use `seedance-1-5-pro-251215` for all video generation.** It completes in ~60-120s and produces 720p 16:9 video at 24fps.

---

## Vision API — Image Input

### DO NOT use external URLs

BytePlus servers cannot download images from many hosts (Wikipedia, etc.). You will get:

```
Error while downloading: https://..., status code: 403
```

### DO use base64 data URLs

```python
# Convert frame to base64
data_url = f"data:image/jpeg;base64,{base64_string}"

response = client.responses.create(
    model="seed-2-0-pro-260328",
    input=[{
        "role": "user",
        "content": [
            {"type": "input_image", "image_url": data_url},
            {"type": "input_text", "text": "Find the cup in this image..."},
        ],
    }],
)
```

The `image_url` field accepts `data:image/png;base64,...` and `data:image/jpeg;base64,...` formats. JPEG at quality 0.7 is a good balance of size vs detail for webcam frames.

---

## Visual Grounding (Object Detection)

Use `seed-2-0-pro-260328` with a structured prompt. It reliably returns JSON bounding boxes.

### Prompt that works

```
You are an object detection assistant.
Find the "{object_name}" in this image.
Return ONLY a JSON object:
{"found": true, "label": "cup", "bbox": [x, y, width, height], "confidence": 0.0-1.0}
where bbox is pixel coordinates.
If not found return {"found": false}.
No other text.
```

### Tested result

Input: 200x200 synthetic image with a brown rectangle.
Output: `{"found": true, "label": "cup", "bbox": [56, 39, 80, 101], "confidence": 0.9}`

The bbox values are pixel coordinates. The model understands image dimensions and returns reasonable coordinates.

### Latency for tracking

Each detection call takes ~3-6 seconds. This means:
- You CANNOT poll every 300ms as originally planned
- Realistic polling: one frame at a time, ~3-6s between bbox updates
- Use lerp smoothing on the frontend (factor 0.15) to fill the gaps
- Throttle: skip incoming frames while a detection call is in flight

---

## LLM — Action Labeling

`seed-2-0-lite-260228` reliably labels trajectory data into action phases when given the right prompt.

### Prompt that works

```
Object: cup. Trajectory: [{"t": 0, "center": [200, 300]}, ...]
Label action phases. Return ONLY JSON:
{"actions": [{"t_start_ms": 0, "t_end_ms": 500, "phase": "idle"}, ...]}
Phases: idle, reach, grasp, lift, move, place. No other text.
```

### Tested result

Returns clean JSON with 6 phases correctly segmented by time. The model infers motion direction from center-point displacement.

---

## LLM — Intent Parsing

### Prompt that works

```
Parse this voice command into JSON. Command: "track the cup"
Return ONLY: {"intent": "track", "target_object": "cup"}
No other text.
```

Returns exact JSON. The "No other text" instruction is critical — without it the model adds explanations.

---

## Seedance Video Generation

### Create a task

```python
result = client.content_generation.tasks.create(
    model="seedance-1-5-pro-251215",
    content=[
        {"type": "text", "text": "A hand picks up a cup from a desk..."},
    ],
    generate_audio=False,
    ratio="16:9",
    duration=5,        # seconds (4-15)
    watermark=False,
)
task_id = result.id
```

### With reference video

```python
content=[
    {"type": "text", "text": "Recreate this motion in a warehouse..."},
    {
        "type": "video_url",
        "video_url": {"url": "https://hosted-clip-url.mp4"},
        "role": "reference_video",
    },
]
```

### With reference image

```python
{
    "type": "image_url",
    "image_url": {"url": "https://hosted-image-url.jpg"},
    "role": "reference_image",
}
```

### Poll for completion

```python
result = client.content_generation.tasks.get(task_id=task_id)
d = result.to_dict()
# d["status"] is: "queued" | "running" | "succeeded" | "failed"
# d["content"]["video_url"] has the output URL when succeeded
```

Poll every 15 seconds. Typical completion: 60-120 seconds for `seedance-1-5-pro-251215`.

### Output format (from `.to_dict()`)

```json
{
  "id": "cgt-20260419062950-8wpjp",
  "model": "seedance-1-5-pro-251215",
  "status": "succeeded",
  "content": {
    "video_url": "https://ark-content-generation-ap-southeast-1.tos-ap-southeast-1.volces.com/seedance-1-5-pro/xxx.mp4?X-Tos-Algorithm=..."
  },
  "usage": {"completion_tokens": 108900, "total_tokens": 108900},
  "framespersecond": 24,
  "duration": 5,
  "ratio": "16:9",
  "resolution": "720p"
}
```

The `video_url` is a signed URL that expires in 24 hours. Download or proxy it if you need to keep it.

### List all tasks

```python
tasks = client.content_generation.tasks.list()
d = tasks.to_dict()
# d["total"] = count
# d["items"] = [{"id": ..., "status": ..., "model": ...}, ...]
```

### Parameters reference

| Param | Values | Default |
|---|---|---|
| `model` | `seedance-1-5-pro-251215` (recommended) | required |
| `duration` | 4–15 seconds | required |
| `ratio` | `16:9`, `9:16`, `1:1`, `4:3`, `3:4`, `21:9`, `adaptive` | required |
| `generate_audio` | `True` / `False` | `True` |
| `watermark` | `True` / `False` | `True` |
| `content` | Array of text + image/video refs | required |

### Content array limits

- 0–9 images
- 0–3 videos
- Text + media combined in one array
- Images use `role: "reference_image"`, videos use `role: "reference_video"`

---

## Architecture Gotchas

1. **Detection throttling is mandatory.** The vision API takes 3-6s per call. If the frontend sends frames every 400ms, you MUST drop frames while a call is in flight. Otherwise you'll queue up hundreds of API calls.

2. **Seedance jobs should be fire-and-forget with polling.** Don't `await` a single job — submit all variations at once, then poll them all in a loop every 15s, broadcasting progress to the frontend as each completes.

3. **The hackathon API key is shared.** All teams use the same key. Seedance 2.0 is completely congested. Use 1.5 Pro. LLM and Vision models are fine — no queue issues there.

4. **Video URLs from Seedance expire in 24 hours.** If you need to keep them, download the video to local storage or re-host it.

5. **The `responses.create()` API uses `input` not `messages`.** It's not the OpenAI chat format. Content items use `input_text` and `input_image`, not `text` and `image_url`.

---

## Quick Copy-Paste: Working Client

```python
import os, json
from dotenv import load_dotenv
from byteplussdkarkruntime import Ark

load_dotenv()
client = Ark(
    base_url="https://ark.ap-southeast.bytepluses.com/api/v3",
    api_key=os.getenv("ARK_API_KEY"),
)

# --- Text LLM ---
r = client.responses.create(model="seed-2-0-lite-260228", input="Say hello")

# --- Vision (base64) ---
r = client.responses.create(
    model="seed-2-0-pro-260328",
    input=[{"role": "user", "content": [
        {"type": "input_image", "image_url": "data:image/jpeg;base64,..."},
        {"type": "input_text", "text": "What do you see?"},
    ]}],
)

# --- Seedance ---
r = client.content_generation.tasks.create(
    model="seedance-1-5-pro-251215",
    content=[{"type": "text", "text": "A cup on a desk..."}],
    generate_audio=False, ratio="16:9", duration=5, watermark=False,
)
task_id = r.id
# Poll: client.content_generation.tasks.get(task_id=task_id).to_dict()
```

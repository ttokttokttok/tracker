#!/bin/bash
# Push pipeline data to Butterbase
# Usage: ./push_to_butterbase.sh <app_id> <service_key>

set -e

APP_ID="${1:?Usage: ./push_to_butterbase.sh <app_id> <service_key>}"
SK="${2:?Usage: ./push_to_butterbase.sh <app_id> <service_key>}"
BASE="https://api.butterbase.ai"

echo "=== Pushing to Butterbase (app: $APP_ID) ==="

# Step 1: Apply schema
echo ""
echo "--- Applying schema ---"
curl -s -X POST "$BASE/v1/$APP_ID/schema/apply" \
  -H "Authorization: Bearer $SK" \
  -H "Content-Type: application/json" \
  -d @butterbase_schema.json | jq .

echo ""
echo "--- Schema applied ---"

# Step 2: Insert run
echo ""
echo "--- Inserting run ---"
RUN_RESP=$(curl -s -X POST "$BASE/v1/$APP_ID/runs" \
  -H "Authorization: Bearer $SK" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Can Pickup Demo",
    "status": "complete",
    "target_object": "can",
    "action_label": "pick_and_place",
    "source_video_count": 1,
    "tracked_object_count": 3,
    "synthetic_output_count": 2,
    "duration_ms": 5041
  }')
echo "$RUN_RESP" | jq .
RUN_ID=$(echo "$RUN_RESP" | jq -r '.id')
echo "Run ID: $RUN_ID"

# Step 3: Insert pipeline
echo ""
echo "--- Inserting pipeline ---"
PIPE_RESP=$(curl -s -X POST "$BASE/v1/$APP_ID/pipelines" \
  -H "Authorization: Bearer $SK" \
  -H "Content-Type: application/json" \
  -d "{
    \"run_id\": \"$RUN_ID\",
    \"label\": \"Front View\",
    \"status\": \"complete\",
    \"video_url\": \"/media/source.mp4\",
    \"video_filename\": \"source.mp4\",
    \"duration_ms\": 5041,
    \"video_width\": 1280,
    \"video_height\": 720,
    \"detected_objects\": [
      {\"track_id\": \"hand_right_001\", \"label\": \"right_hand\", \"type\": \"actor_part\", \"color\": \"#35d0ff\"},
      {\"track_id\": \"can_001\", \"label\": \"can\", \"type\": \"manipulated_object\", \"color\": \"#7cf29a\"},
      {\"track_id\": \"table_001\", \"label\": \"table\", \"type\": \"support_surface\", \"color\": \"#5c5c6e\"}
    ],
    \"stage_status\": {
      \"source_video\": \"complete\",
      \"detection\": \"complete\",
      \"tracking\": \"complete\",
      \"annotations\": \"complete\",
      \"world_model\": \"complete\",
      \"synthetic_outputs\": \"complete\"
    }
  }")
echo "$PIPE_RESP" | jq .
PIPE_ID=$(echo "$PIPE_RESP" | jq -r '.id')
echo "Pipeline ID: $PIPE_ID"

# Step 4: Insert tracks (read from seed data)
echo ""
echo "--- Inserting tracks ---"

# We'll read the actual detection data from our seed JSON
SEED_JSON="../pipeline/output/seed_data.json"

if [ -f "$SEED_JSON" ]; then
  # Insert each track from seed data
  for i in 0 1 2; do
    TRACK=$(jq -c ".tracks[$i]" "$SEED_JSON")
    LABEL=$(echo "$TRACK" | jq -r '.label')
    TYPE=$(echo "$TRACK" | jq -r '.type')
    COLOR=$(echo "$TRACK" | jq -r '.color')
    FRAMES=$(echo "$TRACK" | jq -c '.frames')

    echo "  Inserting track: $LABEL"
    curl -s -X POST "$BASE/v1/$APP_ID/tracks" \
      -H "Authorization: Bearer $SK" \
      -H "Content-Type: application/json" \
      -d "{
        \"pipeline_id\": \"$PIPE_ID\",
        \"label\": \"$LABEL\",
        \"track_type\": \"$TYPE\",
        \"color\": \"$COLOR\",
        \"frames\": $FRAMES
      }" | jq -c '.id'
  done
else
  echo "  No seed_data.json found, inserting placeholder tracks"
fi

# Step 5: Insert world model
echo ""
echo "--- Inserting world model ---"

if [ -f "$SEED_JSON" ]; then
  WM_OBJECTS=$(jq -c '.worldModel.objects' "$SEED_JSON")
  WM_ACTIONS=$(jq -c '.worldModel.actions' "$SEED_JSON")
  WM_RELATIONS=$(jq -c '.worldModel.relations' "$SEED_JSON")
  WM_DURATION=$(jq '.worldModel.duration_ms' "$SEED_JSON")

  curl -s -X POST "$BASE/v1/$APP_ID/world_models" \
    -H "Authorization: Bearer $SK" \
    -H "Content-Type: application/json" \
    -d "{
      \"pipeline_id\": \"$PIPE_ID\",
      \"target_object\": \"can\",
      \"action_label\": \"pick_and_place\",
      \"duration_ms\": $WM_DURATION,
      \"objects\": $WM_OBJECTS,
      \"actions\": $WM_ACTIONS,
      \"relations\": $WM_RELATIONS
    }" | jq .
fi

# Step 6: Insert synthetic outputs
echo ""
echo "--- Inserting synthetic outputs ---"

if [ -f "$SEED_JSON" ]; then
  COUNT=$(jq '.syntheticOutputs | length' "$SEED_JSON")
  for i in $(seq 0 $((COUNT - 1))); do
    SYN=$(jq -c ".syntheticOutputs[$i]" "$SEED_JSON")
    LABEL=$(echo "$SYN" | jq -r '.label')
    STATUS=$(echo "$SYN" | jq -r '.status')
    PROVIDER=$(echo "$SYN" | jq -r '.provider')
    PROMPT=$(echo "$SYN" | jq -r '.prompt')
    CONSTRAINTS=$(echo "$SYN" | jq -c '.constraints')
    VIDEO_URL=$(echo "$SYN" | jq -r '.video_url')

    echo "  Inserting synthetic: $LABEL ($STATUS)"
    curl -s -X POST "$BASE/v1/$APP_ID/synthetic_outputs" \
      -H "Authorization: Bearer $SK" \
      -H "Content-Type: application/json" \
      -d "{
        \"pipeline_id\": \"$PIPE_ID\",
        \"run_id\": \"$RUN_ID\",
        \"label\": \"$LABEL\",
        \"status\": \"$STATUS\",
        \"provider\": \"$PROVIDER\",
        \"prompt\": $(echo "$PROMPT" | jq -Rs .),
        \"constraints\": $CONSTRAINTS,
        \"video_url\": \"$VIDEO_URL\"
      }" | jq -c '.id'
  done
fi

echo ""
echo "=== Done! Data pushed to Butterbase ==="
echo "  App ID: $APP_ID"
echo "  Run ID: $RUN_ID"
echo "  Pipeline ID: $PIPE_ID"
echo ""
echo "  API: $BASE/v1/$APP_ID/runs"
echo "  API: $BASE/v1/$APP_ID/pipelines"
echo "  API: $BASE/v1/$APP_ID/tracks"
echo "  API: $BASE/v1/$APP_ID/world_models"
echo "  API: $BASE/v1/$APP_ID/synthetic_outputs"

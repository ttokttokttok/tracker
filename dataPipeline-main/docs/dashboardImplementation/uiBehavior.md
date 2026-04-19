# Dashboard UI Behavior

## Main User Story

The user opens the dashboard, selects a past run, chooses a source-video pipeline, plays the video, sees overlays for tracked objects such as hands and cans, inspects the generated data, and reviews synthetic outputs generated from that same pipeline.

## Run Selection

When a run is selected:

1. Load run metadata.
2. Load source pipeline list.
3. Select the first complete or most recent pipeline.
4. Load its tracks, annotations, world model, and synthetic outputs.
5. Render video workspace.

## Source Pipeline Selection

When a source pipeline is selected:

1. Update source video.
2. Reset playback time to zero.
3. Load pipeline-specific tracks.
4. Load pipeline-specific annotation frames.
5. Load pipeline-specific world model.
6. Load pipeline-specific synthetic outputs.

Do not share bbox overlays across source videos. Each source video has its own camera coordinates.

## Video Overlay Behavior

The overlay is synchronized to the source video current time.

On video `timeupdate` or animation frame:

1. Read `currentTime`.
2. Convert to milliseconds.
3. Find nearest annotation frame or interpolate between frames.
4. Draw visible object overlays.
5. Show active action phase.
6. Update timeline playhead.

### Overlay Rules

- Show manipulated object by default.
- Show hands by default.
- Allow toggling support surfaces and background objects.
- Use stable colors per track id.
- Show confidence only when useful or on hover.
- Mark weak detections with dashed borders.
- Hide lost tracks instead of showing stale boxes.

## Timeline Behavior

The timeline shows action phases and tracking health.

Required interactions:

- Click phase to jump video to phase start.
- Drag playhead to scrub video.
- Hover phase to show timing.
- Click weak tracking segment to inspect annotation data.

## Data Inspector Behavior

The data inspector should always be tied to the selected pipeline and current video timestamp.

Tabs:

- Summary.
- Objects.
- Tracks.
- Actions.
- Relations.
- World Model JSON.
- Annotation JSON.
- Logs.

At a specific timestamp, the inspector should show:

- active action phase,
- visible objects,
- current bbox values,
- current relations,
- confidence values.

## Synthetic Output Behavior

Synthetic output cards are tied to the selected pipeline.

Each card shows:

- variation label,
- status,
- generated video preview,
- prompt used,
- source pipeline id,
- source world-model id.

When a generated video is selected:

1. Show source video and generated video side by side.
2. Keep source annotation timeline visible.
3. Show prompt constraints.
4. Show whether output succeeded, failed, or needs review.

## Multi-Video Behavior

For runs with two source videos:

- Default to a single selected pipeline view.
- Offer compare mode.
- Compare mode shows both source videos side by side.
- Each video keeps its own overlay layer.
- Shared action phase timeline can appear under both videos.

## Loading States

### Run Loading

Show run cards as skeletons only while the run list loads.

### Pipeline Loading

Keep the run workspace visible and show loading state inside the pipeline panel.

### Annotation Loading

Show source video immediately if available, then add overlays when annotation data arrives.

### Synthetic Loading

Show generation job cards as soon as jobs exist.

## Error States

### Missing Source Video

```text
This pipeline has no source video. Upload a video to start data generation.
```

### Missing Annotations

```text
No annotations have been generated yet. Run the data-generation pipeline for this source video.
```

### Generation Failed

```text
Seedance generation failed. Review the prompt and source video URL, then retry.
```

## Visual Quality Requirements

- The video should be the visual anchor.
- Overlays must be readable but not distracting.
- Synthetic outputs should feel connected to the source pipeline.
- The user should understand the source-to-data-to-synthetic flow without reading documentation.
- Avoid admin-table-heavy layouts.


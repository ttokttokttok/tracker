# Dashboard And UI Specification

## Product Feel

The app should feel like a premium video review and dataset-generation studio.

It should not feel like a plain CRUD dashboard. The main visual focus should be media: source recordings, overlays, generated videos, timelines, and run thumbnails.

## Routes

| Route | Purpose |
| --- | --- |
| `/record` | Create a new recorded demonstration and launch generation. |
| `/dashboard` | Review past runs, inspect annotations, compare videos, and export datasets. |

## `/record` Visual Layout

```text
------------------------------------------------------------
| Header: PhysicalAI Dataset Studio     Run status / user   |
------------------------------------------------------------
|                                                          |
|  Large live camera / recording stage                     |
|  - bbox overlay                                          |
|  - target label                                          |
|  - recording indicator                                   |
|  - confidence/status                                     |
|                                                          |
|----------------------------------------------------------|
| Command dock: target object, track, record, stop, generate|
|----------------------------------------------------------|
| Timeline strip: recording time, phases, confidence marks  |
|----------------------------------------------------------|
| Bottom drawer: world model preview / logs / raw JSON      |
------------------------------------------------------------
| Right rail: Seedance generation queue                     |
------------------------------------------------------------
```

### `/record` Components

- `CameraStage`
- `TrackingOverlay`
- `CommandDock`
- `RecordingControls`
- `GenerationQueue`
- `WorldModelDrawer`
- `StatusTimeline`

### `/record` Interaction Details

- Tracking overlay should animate smoothly between bbox updates.
- Recording should show a clear red state and elapsed time.
- When recording stops, the UI should transition into processing.
- Generation cards should appear immediately after jobs are created.
- Each generation card should show queued, running, succeeded, or failed state.

## `/dashboard` Visual Layout

```text
------------------------------------------------------------
| Header: Dashboard   Search / filters / export             |
------------------------------------------------------------
| Left rail              | Main review workspace            |
| - run thumbnails       |                                  |
| - object filters       | Source video  | Selected variant |
| - status filters       | with overlay  | generated video  |
|                        |                                  |
|                        | Action timeline                  |
|                        |                                  |
|                        | Tabs: annotations, world model,  |
|                        | prompts, logs, export manifest   |
------------------------------------------------------------
| Right rail: variation cards and job status                |
------------------------------------------------------------
```

### `/dashboard` Components

- `RunSidebar`
- `RunSearch`
- `RunStatusFilters`
- `VideoComparison`
- `AnnotationOverlayPlayer`
- `ActionTimeline`
- `VariationRail`
- `WorldModelViewer`
- `PromptViewer`
- `ExportPanel`

## Design Direction

### Media Stage

The video areas should be large, sharp, and central. Use the recorded media as the visual anchor of the UI.

### Color And Style

Use a refined, high-contrast product style:

- near-black or graphite app background,
- white and soft-gray text,
- cyan or green tracking accents,
- red only for active recording,
- amber only for warnings,
- thin borders,
- subtle shadows,
- glass-like panels used sparingly.

Avoid a one-color theme. The interface should use status colors meaningfully.

### Typography

- Use clear sans-serif type.
- Make run names, object names, and current state easy to scan.
- Keep JSON readable with monospace formatting.

### Motion

Use motion for state changes only:

- recording pulse,
- generation progress,
- bbox smoothing,
- drawer open/close,
- timeline scrubber.

Do not add decorative animation that competes with the video.

## Dashboard Data Views

### Source Video View

Must show:

- original recording,
- bbox overlay,
- current timestamp,
- active action phase,
- object label and confidence.

### Generated Variation View

Must show:

- generated video,
- variation label,
- prompt used,
- generation status,
- source run link,
- inherited world-model id.

### Timeline View

Must show:

- action phase segments,
- confidence graph or markers,
- weak/lost tracking markers,
- generation-relevant event markers.

### World Model View

Must show:

- formatted JSON,
- object list,
- relation list,
- action phases,
- track summary.

### Export View

Must show:

- source video included,
- annotations included,
- world model included,
- generated variations included,
- manifest preview,
- export button.

## Empty States

### No Runs

Message:

```text
No runs yet. Record a demonstration to create your first dataset sample.
```

Primary action:

```text
Go to Recording Studio
```

### Generation Pending

Message:

```text
Seedance variations are still generating. Completed videos will appear here automatically.
```

### Missing Annotation

Message:

```text
Annotations are unavailable for this run. Reprocess the source video to rebuild them.
```

## Quality Bar

The UI should make the demo easy to understand in under 10 seconds:

- The source action is obvious.
- The tracked object is obvious.
- The generated variations are obvious.
- The world-model data is visible but not overwhelming.
- The exportable dataset story is clear.


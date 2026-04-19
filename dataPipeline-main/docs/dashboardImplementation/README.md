# Dashboard Implementation Docs

This folder defines how to build the dashboard as a complete module-driven product, not as a loose mock shell.

The dashboard is the review and generation workspace for past runs. A run contains one or more source-video pipelines. Each source-video pipeline shows the original video, detected objects, tracking overlays, annotation data, world-model data, and synthetic videos generated from that source.

## Implementation Principle

Build complete vertical modules instead of disconnected placeholders.

Do not build:

- empty UI shells,
- fake buttons with no data contract,
- static panels that cannot connect to a run,
- synthetic-output cards that are not tied to a source pipeline,
- annotation displays that cannot sync with video playback.

Build each module with:

- data shape,
- API contract,
- UI component,
- state behavior,
- error and loading states,
- verification checklist.

## Documents

| File | Purpose |
| --- | --- |
| [implementationPlan.md](./implementationPlan.md) | Phased module-driven build order. |
| [modules.md](./modules.md) | Dashboard modules and responsibilities. |
| [dataModel.md](./dataModel.md) | Run, source pipeline, annotations, world model, and synthetic output schemas. |
| [apiContracts.md](./apiContracts.md) | Backend endpoints needed by the dashboard. |
| [uiBehavior.md](./uiBehavior.md) | How playback, overlays, timelines, panels, and generation state should behave. |
| [deliveryChecklist.md](./deliveryChecklist.md) | Definition of done for the dashboard implementation. |

## Dashboard Product Shape

```text
/dashboard
  Run Library
    -> select past run

  Run Workspace
    -> source-video pipelines
    -> video playback with synced overlays
    -> object/hand tracking data
    -> annotations and world model
    -> synthetic data generated from each pipeline
    -> export package
```

## Core Concept

A run is not just a video.

A run is a container for one or more data-generation pipelines:

```text
Run
  Source Pipeline A
    source video
    detected objects
    tracking overlays
    annotations
    world model
    synthetic outputs

  Source Pipeline B
    source video
    detected objects
    tracking overlays
    annotations
    world model
    synthetic outputs
```

This lets the dashboard support one or two source videos per run while keeping the data clean.


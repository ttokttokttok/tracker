# Dashboard Modules

## Module Overview

The dashboard should be built as modules with clear ownership.

```text
DashboardShell
  RunLibrary
  RunWorkspace
    SourcePipelineTabs
    PipelineStageStrip
    SourceVideoReview
    AnnotationTimeline
    DataInspector
    SyntheticOutputWorkspace
    ExportPanel
```

## DashboardShell

### Responsibility

Own the page layout and selected run state.

### Inputs

- Run list.
- Selected run id.
- Global loading/error state.

### Outputs

- Selected run.
- Navigation actions.

### UI

- Header.
- Left run library.
- Main run workspace.
- Right synthetic/output rail if screen width allows.

## RunLibrary

### Responsibility

Show past runs and let the user choose one.

### Data

- run id,
- run name,
- thumbnail,
- target object,
- action label,
- source video count,
- synthetic output count,
- status,
- created timestamp.

### UI Requirements

- Visual run cards.
- Search.
- Status filters.
- Object/action filters.
- Empty state.

## RunWorkspace

### Responsibility

Show the selected run and all its source-video pipelines.

### Data

- selected run,
- selected source pipeline,
- run-level world model summary,
- pipeline list.

### UI Requirements

- Run title.
- Run status.
- Source pipeline tabs.
- Main video and annotation area.
- Synthetic data area.

## SourcePipelineTabs

### Responsibility

Switch between source-video pipelines.

### Data

- pipeline id,
- source video label,
- pipeline status,
- generated output count.

### UI Requirements

- One tab per source video.
- Clear status: uploaded, processing, annotated, generating, complete, failed.
- Support one or two source videos in MVP.

## PipelineStageStrip

### Responsibility

Show where a source video is in the data-generation pipeline.

### Stages

1. Source video.
2. Detection.
3. Tracking.
4. Annotations.
5. World model.
6. Synthetic outputs.

### UI Requirements

- Each stage has status.
- Click stage to focus relevant panel.
- Failed stage shows reason.

## SourceVideoReview

### Responsibility

Play the source video and render synced overlays.

### Data

- source video URL,
- current playback time,
- object tracks,
- active action phase,
- selected overlay tracks.

### UI Requirements

- Video player.
- Overlay layer.
- Bbox labels.
- Confidence badges.
- Current action phase badge.
- Track visibility toggles.

## AnnotationTimeline

### Responsibility

Show the temporal structure of the source pipeline.

### Data

- action phases,
- tracking confidence over time,
- weak/lost tracking segments,
- generation events.

### UI Requirements

- Scrubbable timeline.
- Phase labels.
- Current-time playhead.
- Click phase to jump video.

## DataInspector

### Responsibility

Expose generated data for review.

### Tabs

- Objects.
- Tracks.
- Actions.
- Relations.
- World Model JSON.
- Annotation JSON.
- Logs.

### UI Requirements

- Human-readable summary first.
- Raw JSON available.
- Copy/export controls.

## SyntheticOutputWorkspace

### Responsibility

Show synthetic videos generated from the selected source pipeline.

### Data

- synthetic output records,
- Seedance job status,
- prompt,
- constraints,
- generated video URL,
- parent pipeline id.

### UI Requirements

- Output cards.
- Video preview.
- Status indicators.
- Prompt viewer.
- Compare with source action.
- Regenerate action.

## ExportPanel

### Responsibility

Export a complete dataset package.

### Includes

- source videos,
- annotations,
- world model,
- synthetic videos,
- generation prompts,
- manifest.

### UI Requirements

- Manifest preview.
- Export status.
- Clear errors for missing data.


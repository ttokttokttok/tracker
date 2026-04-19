# Dashboard Delivery Checklist

## Demo Completeness

- [ ] Dashboard renders at `/` with dark modern theme.
- [ ] One seeded run is visible with name, status, and metadata.
- [ ] Source video plays in the workspace.
- [ ] Bbox overlays render on top of video in sync with playback.
- [ ] Hand and object tracks have stable colors and labels.
- [ ] Scrubbing and pausing update overlays correctly.
- [ ] Action phase timeline shows colored segments.
- [ ] Clicking a phase jumps the video.
- [ ] Data inspector shows objects, actions, relations, and world model.
- [ ] Raw JSON is viewable in the inspector.
- [ ] Synthetic output gallery shows generated video cards.
- [ ] Each card shows label, status, prompt, and video preview.
- [ ] Source and synthetic video can be compared.

## E2E Pipeline

- [ ] Pipeline script runs against a source video.
- [ ] Object detection produces per-frame bbox data.
- [ ] Action labeling produces phase segments.
- [ ] World model is assembled from tracks and actions.
- [ ] Seedance jobs are submitted and polled.
- [ ] All output is written as JSON seed files.
- [ ] Dashboard renders the pipeline output without changes.

## UX Quality

- [ ] Dark theme is consistent and polished.
- [ ] Video is the visual anchor of the workspace.
- [ ] Typography is clean with strong hierarchy.
- [ ] State changes are visible.
- [ ] The source-to-data-to-synthetic story is obvious without documentation.

## Engineering Quality

- [ ] Components map to clear modules.
- [ ] Seed data is typed and validated.
- [ ] Overlay rendering does not mutate source data.
- [ ] Video timestamp sync works with scrubbing and pausing.

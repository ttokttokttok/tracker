import { useState } from 'react';
import RunHeader from './components/RunHeader';
import VideoPlayer from './components/VideoPlayer';
import AnnotationTimeline from './components/AnnotationTimeline';
import SyntheticTabs from './components/SyntheticTabs';
import DataStrip from './components/DataStrip';
import { useVideoSync } from './hooks/useVideoSync';
import { run, pipeline, tracks, worldModel, syntheticOutputs } from './data/seedRun';

export default function App() {
  const [visibleTracks, setVisibleTracks] = useState(() => {
    const initial = {};
    pipeline.detected_objects.forEach((obj) => {
      initial[obj.track_id] = obj.type !== 'support_surface';
    });
    return initial;
  });

  const toggleTrack = (trackId) => {
    setVisibleTracks((prev) => ({ ...prev, [trackId]: !prev[trackId] }));
  };

  const {
    videoRef,
    currentTimeMs,
    isPlaying,
    overlays,
    currentPhase,
    currentRelations,
    seekTo,
    onPlay,
    onPause,
    onSeeked,
  } = useVideoSync(tracks, worldModel);

  return (
    <div className="h-screen flex flex-col bg-surface-0 overflow-hidden">
      {/* Slim header */}
      <RunHeader run={run} pipeline={pipeline} />

      {/* Main workspace — no scroll */}
      <div className="flex-1 flex flex-col min-h-0 p-4 gap-3">
        {/* Top row: source video + synthetic tabs */}
        <div className="flex-1 flex gap-4 min-h-0">
          {/* Source video — compact left column */}
          <div className="w-[42%] flex flex-col gap-2 min-h-0">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">Source Video</h2>
              <div className="flex items-center gap-1.5">
                {pipeline.detected_objects.map((obj) => {
                  const vis = visibleTracks[obj.track_id];
                  return (
                    <button
                      key={obj.track_id}
                      onClick={() => toggleTrack(obj.track_id)}
                      className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium border transition-all cursor-pointer ${
                        vis ? '' : 'opacity-40 bg-surface-2 border-border text-text-muted'
                      }`}
                      style={vis ? {
                        backgroundColor: obj.color + '18',
                        borderColor: obj.color + '40',
                        color: obj.color,
                      } : {}}
                    >
                      <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: obj.color }} />
                      {obj.label}
                    </button>
                  );
                })}
              </div>
            </div>
            <div className="flex-1 min-h-0">
              <VideoPlayer
                videoUrl={pipeline.source_video.url}
                videoRef={videoRef}
                overlays={overlays}
                currentPhase={currentPhase}
                currentTimeMs={currentTimeMs}
                durationMs={pipeline.source_video.duration_ms}
                onPlay={onPlay}
                onPause={onPause}
                onSeeked={onSeeked}
                visibleTracks={visibleTracks}
                videoWidth={pipeline.source_video.width}
                videoHeight={pipeline.source_video.height}
              />
            </div>
          </div>

          {/* Synthetic outputs — tabbed right column */}
          <div className="flex-1 flex flex-col min-h-0">
            <SyntheticTabs outputs={syntheticOutputs} />
          </div>
        </div>

        {/* Timeline — full width */}
        <AnnotationTimeline
          actions={worldModel.actions}
          durationMs={worldModel.duration_ms}
          currentTimeMs={currentTimeMs}
          onSeek={seekTo}
        />

        {/* Data strip — compact bottom bar */}
        <DataStrip
          pipeline={pipeline}
          overlays={overlays}
          currentPhase={currentPhase}
          currentRelations={currentRelations}
          worldModel={worldModel}
          currentTimeMs={currentTimeMs}
        />
      </div>
    </div>
  );
}

import { useState, useCallback, useRef, useEffect } from 'react';

// Find the frame closest to the given timestamp using binary search
function findClosestFrame(frames, tMs) {
  if (!frames || frames.length === 0) return null;
  if (frames.length === 1) return frames[0];
  if (tMs <= frames[0].t_ms) return frames[0];
  if (tMs >= frames[frames.length - 1].t_ms) return frames[frames.length - 1];

  let lo = 0;
  let hi = frames.length - 1;
  while (lo < hi - 1) {
    const mid = (lo + hi) >> 1;
    if (frames[mid].t_ms <= tMs) lo = mid;
    else hi = mid;
  }

  // Interpolate between lo and hi
  const f0 = frames[lo];
  const f1 = frames[hi];
  const t = (tMs - f0.t_ms) / (f1.t_ms - f0.t_ms);

  return {
    t_ms: tMs,
    bbox: f0.bbox.map((v, i) => Math.round(v + (f1.bbox[i] - v) * t)),
    confidence: f0.confidence + (f1.confidence - f0.confidence) * t,
    visible: f0.visible && f1.visible,
  };
}

export function useVideoSync(tracks, worldModel) {
  const [currentTimeMs, setCurrentTimeMs] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const videoRef = useRef(null);
  const animFrameRef = useRef(null);

  const syncLoop = useCallback(() => {
    if (videoRef.current && !videoRef.current.paused) {
      setCurrentTimeMs(videoRef.current.currentTime * 1000);
      animFrameRef.current = requestAnimationFrame(syncLoop);
    }
  }, []);

  const onPlay = useCallback(() => {
    setIsPlaying(true);
    animFrameRef.current = requestAnimationFrame(syncLoop);
  }, [syncLoop]);

  const onPause = useCallback(() => {
    setIsPlaying(false);
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    if (videoRef.current) setCurrentTimeMs(videoRef.current.currentTime * 1000);
  }, []);

  const onSeeked = useCallback(() => {
    if (videoRef.current) setCurrentTimeMs(videoRef.current.currentTime * 1000);
  }, []);

  const seekTo = useCallback((ms) => {
    if (videoRef.current) {
      videoRef.current.currentTime = ms / 1000;
      setCurrentTimeMs(ms);
    }
  }, []);

  useEffect(() => {
    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, []);

  // Compute current overlays
  const overlays = tracks.map((track) => {
    const frame = findClosestFrame(track.frames, currentTimeMs);
    return {
      track_id: track.track_id,
      label: track.label,
      type: track.type,
      color: track.color,
      frame,
    };
  });

  // Current action phase
  const currentPhase = worldModel?.actions?.find(
    (a) => currentTimeMs >= a.t_start_ms && currentTimeMs < a.t_end_ms
  ) || worldModel?.actions?.[worldModel.actions.length - 1];

  // Current relations
  const currentRelations = worldModel?.relations?.filter(
    (r) => currentTimeMs >= r.t_start_ms && currentTimeMs < r.t_end_ms
  ) || [];

  return {
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
  };
}

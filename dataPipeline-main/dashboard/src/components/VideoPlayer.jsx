import { useEffect, useRef, useCallback } from 'react';

const PHASE_COLORS = {
  idle: '#5c5c6e',
  reach: '#35d0ff',
  grasp: '#ffb347',
  lift_and_move: '#7cf29a',
  place: '#ff6b6b',
};

export default function VideoPlayer({
  videoUrl,
  videoRef,
  overlays,
  currentPhase,
  currentTimeMs,
  durationMs,
  onPlay,
  onPause,
  onSeeked,
  visibleTracks,
  videoWidth = 1280,
  videoHeight = 720,
}) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);

  const drawOverlays = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const rect = container.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;

    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const scaleX = rect.width / videoWidth;
    const scaleY = rect.height / videoHeight;

    for (const overlay of overlays) {
      if (!visibleTracks[overlay.track_id]) continue;
      if (!overlay.frame || !overlay.frame.visible) continue;

      const [x, y, w, h] = overlay.frame.bbox;
      const sx = x * scaleX;
      const sy = y * scaleY;
      const sw = w * scaleX;
      const sh = h * scaleY;

      const conf = overlay.frame.confidence;
      const isWeak = conf < 0.85;

      ctx.strokeStyle = overlay.color;
      ctx.lineWidth = 2;
      if (isWeak) ctx.setLineDash([6, 4]);
      else ctx.setLineDash([]);
      ctx.strokeRect(sx, sy, sw, sh);

      const label = `${overlay.label} ${(conf * 100).toFixed(0)}%`;
      ctx.font = '10px Inter, system-ui, sans-serif';
      const tw = ctx.measureText(label).width;
      const lh = 16;
      const ly = sy > lh + 2 ? sy - lh - 1 : sy + sh + 1;

      ctx.fillStyle = overlay.color + '30';
      ctx.fillRect(sx, ly, tw + 8, lh);
      ctx.strokeStyle = overlay.color + '60';
      ctx.lineWidth = 1;
      ctx.setLineDash([]);
      ctx.strokeRect(sx, ly, tw + 8, lh);
      ctx.fillStyle = overlay.color;
      ctx.fillText(label, sx + 4, ly + 12);
    }
  }, [overlays, visibleTracks, videoWidth, videoHeight]);

  useEffect(() => { drawOverlays(); }, [drawOverlays]);

  useEffect(() => {
    const h = () => drawOverlays();
    window.addEventListener('resize', h);
    return () => window.removeEventListener('resize', h);
  }, [drawOverlays]);

  const hasVideo = videoUrl && videoUrl.length > 0;
  const progress = durationMs > 0 ? (currentTimeMs / durationMs) * 100 : 0;

  return (
    <div className="h-full flex flex-col gap-1">
      <div
        ref={containerRef}
        className="relative bg-surface-0 rounded-lg overflow-hidden border border-border flex-1 min-h-0 cursor-pointer"
        style={{ aspectRatio: `${videoWidth}/${videoHeight}` }}
        onClick={() => {
          if (!hasVideo) return;
          if (videoRef.current?.paused) videoRef.current.play();
          else videoRef.current?.pause();
        }}
      >
        {hasVideo ? (
          <video
            ref={videoRef}
            src={videoUrl}
            className="w-full h-full object-contain"
            onPlay={onPlay}
            onPause={onPause}
            onSeeked={onSeeked}
            playsInline
            muted
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <div className="text-center">
              <svg className="w-10 h-10 text-text-muted/40 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z" />
              </svg>
              <p className="text-text-muted text-xs">Run pipeline to generate video</p>
            </div>
          </div>
        )}

        <canvas ref={canvasRef} className="absolute inset-0 w-full h-full pointer-events-none" />

        {/* Phase badge */}
        {currentPhase && (
          <div
            className="absolute top-2 left-2 px-2 py-0.5 rounded-full text-[10px] font-semibold backdrop-blur-sm border"
            style={{
              backgroundColor: (PHASE_COLORS[currentPhase.phase] || '#5c5c6e') + '25',
              borderColor: (PHASE_COLORS[currentPhase.phase] || '#5c5c6e') + '50',
              color: PHASE_COLORS[currentPhase.phase] || '#5c5c6e',
            }}
          >
            {currentPhase.phase.replace(/_/g, ' ')}
          </div>
        )}

        {/* Time */}
        <div className="absolute bottom-2 right-2 px-2 py-0.5 rounded bg-black/60 backdrop-blur-sm text-[10px] font-mono text-text-primary">
          {fmt(currentTimeMs)} / {fmt(durationMs)}
        </div>
      </div>

      {/* Thin progress bar */}
      <div className="h-0.5 bg-surface-2 rounded-full overflow-hidden shrink-0">
        <div className="h-full bg-accent-cyan transition-[width] duration-100" style={{ width: `${progress}%` }} />
      </div>
    </div>
  );
}

function fmt(ms) {
  const s = Math.floor(ms / 1000);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}.${Math.floor((ms % 1000) / 100)}`;
}

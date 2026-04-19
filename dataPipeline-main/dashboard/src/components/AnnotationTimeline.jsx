const PHASE_COLORS = {
  idle: '#5c5c6e',
  reach: '#35d0ff',
  grasp: '#ffb347',
  lift_and_move: '#7cf29a',
  place: '#ff6b6b',
};

const PHASE_LABELS = {
  idle: 'Idle',
  reach: 'Reach',
  grasp: 'Grasp',
  lift_and_move: 'Lift & Move',
  place: 'Place',
};

export default function AnnotationTimeline({ actions, durationMs, currentTimeMs, onSeek }) {
  if (!actions || actions.length === 0) return null;

  const playheadPct = durationMs > 0 ? (currentTimeMs / durationMs) * 100 : 0;

  return (
    <div className="bg-surface-1 rounded-lg border border-border px-4 py-2.5 shrink-0">
      <div className="flex items-center gap-4">
        {/* Label */}
        <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider shrink-0 w-16">Timeline</span>

        {/* Bar */}
        <div className="flex-1 relative">
          <div className="flex h-7 rounded overflow-hidden border border-border/50">
            {actions.map((action) => {
              const w = ((action.t_end_ms - action.t_start_ms) / durationMs) * 100;
              const color = PHASE_COLORS[action.phase] || '#5c5c6e';
              const isActive = currentTimeMs >= action.t_start_ms && currentTimeMs < action.t_end_ms;

              return (
                <button
                  key={action.phase + action.t_start_ms}
                  className="relative group transition-all cursor-pointer border-none outline-none"
                  style={{
                    width: `${w}%`,
                    backgroundColor: color + (isActive ? '30' : '12'),
                  }}
                  onClick={() => onSeek(action.t_start_ms)}
                >
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span
                      className="text-[10px] font-medium truncate px-1"
                      style={{ color: isActive ? color : color + '99' }}
                    >
                      {PHASE_LABELS[action.phase] || action.phase}
                    </span>
                  </div>
                  <div className="absolute right-0 top-0.5 bottom-0.5 w-px bg-border/40" />

                  {/* Tooltip */}
                  <div className="absolute -top-8 left-1/2 -translate-x-1/2 hidden group-hover:block z-10">
                    <div className="bg-surface-3 border border-border-bright rounded px-2 py-0.5 text-[10px] text-text-secondary whitespace-nowrap shadow-lg">
                      {(action.t_start_ms / 1000).toFixed(1)}s - {(action.t_end_ms / 1000).toFixed(1)}s
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Playhead */}
          <div
            className="absolute top-0 h-full w-0.5 bg-white z-10 pointer-events-none transition-[left] duration-75"
            style={{ left: `${playheadPct}%` }}
          >
            <div className="absolute -top-0.5 left-1/2 -translate-x-1/2 w-2 h-2 rounded-full bg-white border border-surface-1" />
          </div>
        </div>

        {/* Time */}
        <span className="text-[10px] font-mono text-text-muted shrink-0 w-14 text-right">
          {(currentTimeMs / 1000).toFixed(1)}s / {(durationMs / 1000).toFixed(1)}s
        </span>
      </div>
    </div>
  );
}

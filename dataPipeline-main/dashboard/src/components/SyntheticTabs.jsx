import { useState, useRef } from 'react';

const STATUS = {
  succeeded: { dot: 'bg-accent-green', text: 'text-accent-green', label: 'Generated' },
  running: { dot: 'bg-accent-amber animate-pulse', text: 'text-accent-amber', label: 'Generating...' },
  queued: { dot: 'bg-text-muted', text: 'text-text-muted', label: 'Queued' },
  failed: { dot: 'bg-accent-red', text: 'text-accent-red', label: 'Failed' },
};

export default function SyntheticTabs({ outputs }) {
  const [activeIdx, setActiveIdx] = useState(0);
  const videoRefs = useRef({});
  const active = outputs[activeIdx];

  if (!active) return null;

  const st = STATUS[active.status] || STATUS.queued;
  const hasVideo = active.video_url && active.video_url.length > 0;

  return (
    <div className="h-full flex flex-col min-h-0">
      {/* Tab bar */}
      <div className="flex items-center gap-1 mb-2 shrink-0">
        <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mr-3">Synthetic Outputs</h2>
        {outputs.map((out, i) => {
          const s = STATUS[out.status] || STATUS.queued;
          const isActive = i === activeIdx;
          return (
            <button
              key={out.synthetic_id}
              onClick={() => setActiveIdx(i)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all cursor-pointer ${
                isActive
                  ? 'bg-surface-2 border-border-bright text-text-primary'
                  : 'bg-transparent border-transparent text-text-muted hover:text-text-secondary hover:bg-surface-2/50'
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${s.dot}`} />
              {out.label}
            </button>
          );
        })}
      </div>

      {/* Active output */}
      <div className="flex-1 flex gap-3 min-h-0">
        {/* Video */}
        <div className="flex-1 min-h-0 flex flex-col">
          <div className="flex-1 relative bg-surface-0 rounded-lg overflow-hidden border border-border min-h-0">
            {hasVideo ? (
              <video
                ref={(el) => { videoRefs.current[active.synthetic_id] = el; }}
                key={active.synthetic_id}
                src={active.video_url}
                className="w-full h-full object-contain"
                controls
                muted
                playsInline
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <div className="text-center">
                  {active.status === 'running' ? (
                    <>
                      <div className="w-8 h-8 mx-auto mb-2 border-2 border-accent-amber/30 border-t-accent-amber rounded-full animate-spin" />
                      <p className="text-accent-amber text-xs font-medium">Generating video...</p>
                    </>
                  ) : active.status === 'queued' ? (
                    <>
                      <div className="w-8 h-8 mx-auto mb-2 rounded-full bg-surface-2 border border-border flex items-center justify-center">
                        <div className="w-2 h-2 rounded-full bg-text-muted" />
                      </div>
                      <p className="text-text-muted text-xs">Queued for generation</p>
                    </>
                  ) : (
                    <>
                      <svg className="w-8 h-8 text-accent-red/50 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
                      </svg>
                      <p className="text-accent-red text-xs">Generation failed</p>
                    </>
                  )}
                </div>
              </div>
            )}

            {/* Status badge */}
            <div className={`absolute top-2 right-2 flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold backdrop-blur-sm bg-black/40 ${st.text}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${st.dot}`} />
              {st.label}
            </div>
          </div>
        </div>

        {/* Info panel */}
        <div className="w-[240px] shrink-0 flex flex-col gap-2 min-h-0 overflow-y-auto">
          {/* Generation info */}
          <div className="bg-surface-1 rounded-lg border border-border p-3">
            <div className="text-[10px] text-text-muted uppercase tracking-wider mb-1.5">Generation</div>
            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-text-muted">Provider</span>
                <span className="text-text-primary font-mono text-[10px]">Seedance 1.5 Pro</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Status</span>
                <span className={`font-medium ${st.text}`}>{active.status}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Pipeline</span>
                <span className="text-text-primary font-mono text-[10px]">{active.pipeline_id}</span>
              </div>
            </div>
          </div>

          {/* Prompt */}
          <div className="bg-surface-1 rounded-lg border border-border p-3 flex-1 min-h-0">
            <div className="text-[10px] text-text-muted uppercase tracking-wider mb-1.5">Prompt</div>
            <p className="text-xs text-text-secondary leading-relaxed">{active.prompt}</p>
          </div>

          {/* Constraints */}
          <div className="bg-surface-1 rounded-lg border border-border p-3">
            <div className="text-[10px] text-text-muted uppercase tracking-wider mb-1.5">Constraints</div>
            <div className="space-y-1">
              {active.constraints.map((c, i) => (
                <div key={i} className="text-[10px] text-text-muted px-2 py-1 bg-surface-2 rounded">
                  {c}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

import { useState } from 'react';

const STATUS_STYLES = {
  succeeded: { bg: 'bg-accent-green/15', text: 'text-accent-green', border: 'border-accent-green/30' },
  running: { bg: 'bg-accent-amber/15', text: 'text-accent-amber', border: 'border-accent-amber/30' },
  failed: { bg: 'bg-accent-red/15', text: 'text-accent-red', border: 'border-accent-red/30' },
  queued: { bg: 'bg-text-muted/15', text: 'text-text-muted', border: 'border-text-muted/30' },
};

export default function SyntheticGallery({ outputs, sourceVideoUrl }) {
  const [selectedId, setSelectedId] = useState(null);
  const selected = outputs.find((o) => o.synthetic_id === selectedId);

  return (
    <div className="bg-surface-1 rounded-xl border border-border overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <h3 className="text-sm font-semibold text-text-primary">Synthetic Outputs</h3>
        <span className="text-xs text-text-muted">
          {outputs.filter((o) => o.status === 'succeeded').length}/{outputs.length} generated
        </span>
      </div>

      {/* Gallery grid */}
      <div className="p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {outputs.map((output) => {
            const style = STATUS_STYLES[output.status] || STATUS_STYLES.queued;
            const isSelected = selectedId === output.synthetic_id;
            const hasVideo = output.video_url && output.video_url.length > 0;

            return (
              <button
                key={output.synthetic_id}
                onClick={() => setSelectedId(isSelected ? null : output.synthetic_id)}
                className={`text-left rounded-lg border transition-all cursor-pointer p-0 ${
                  isSelected
                    ? 'border-accent-cyan bg-surface-2 ring-1 ring-accent-cyan/30'
                    : 'border-border bg-surface-2/50 hover:border-border-bright hover:bg-surface-2'
                }`}
              >
                {/* Video preview */}
                <div className="aspect-video bg-surface-0 rounded-t-lg overflow-hidden relative">
                  {hasVideo ? (
                    <video
                      src={output.video_url}
                      className="w-full h-full object-cover"
                      muted
                      playsInline
                      onMouseEnter={(e) => e.target.play()}
                      onMouseLeave={(e) => { e.target.pause(); e.target.currentTime = 0; }}
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <div className="text-center">
                        <svg className="w-8 h-8 text-text-muted/40 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 0 1-1.125-1.125M3.375 19.5h1.5C5.496 19.5 6 18.996 6 18.375m-2.625 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-1.5A1.125 1.125 0 0 1 18 18.375M20.625 4.5H3.375m17.25 0c.621 0 1.125.504 1.125 1.125M20.625 4.5h-1.5C18.504 4.5 18 5.004 18 5.625m3.75 0v1.5c0 .621-.504 1.125-1.125 1.125M3.375 4.5c-.621 0-1.125.504-1.125 1.125M3.375 4.5h1.5C5.496 4.5 6 5.004 6 5.625m-2.625 0v1.5c0 .621.504 1.125 1.125 1.125m0 0h1.5m-1.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m1.5-3.75C5.496 8.25 6 7.746 6 7.125v-1.5M4.875 8.25C5.496 8.25 6 8.754 6 9.375v1.5m0-5.25v5.25m0-5.25C6 5.004 6.504 4.5 7.125 4.5h9.75c.621 0 1.125.504 1.125 1.125m1.125 2.625h1.5m-1.5 0A1.125 1.125 0 0 1 18 7.125v-1.5m1.125 2.625c-.621 0-1.125.504-1.125 1.125v1.5m2.625-2.625c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125M18 5.625v5.25M7.125 12h9.75m-9.75 0A1.125 1.125 0 0 1 6 10.875M7.125 12C6.504 12 6 12.504 6 13.125m0-2.25C6 11.496 5.496 12 4.875 12M18 10.875c0 .621-.504 1.125-1.125 1.125M18 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125m-12 5.25v-5.25m0 5.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125m-12 0v-1.5c0-.621-.504-1.125-1.125-1.125M18 18.375v-5.25m0 5.25v-1.5c0-.621.504-1.125 1.125-1.125M18 13.125v1.5c0 .621.504 1.125 1.125 1.125M18 13.125c0-.621.504-1.125 1.125-1.125M6 13.125v1.5c0 .621-.504 1.125-1.125 1.125M6 13.125C6 12.504 5.496 12 4.875 12m-1.5 0h1.5m-1.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M19.125 12h1.5m0 0c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h1.5m14.25 0h1.5" />
                        </svg>
                        <span className="text-[10px] text-text-muted/40 mt-1 block">No video yet</span>
                      </div>
                    </div>
                  )}

                  {/* Status badge */}
                  <div className={`absolute top-2 right-2 px-2 py-0.5 rounded text-[10px] font-semibold ${style.bg} ${style.text} ${style.border} border`}>
                    {output.status}
                  </div>
                </div>

                {/* Card info */}
                <div className="p-3">
                  <div className="text-sm font-medium text-text-primary">{output.label}</div>
                  <div className="text-xs text-text-muted mt-1 line-clamp-2">{output.prompt}</div>
                </div>
              </button>
            );
          })}
        </div>

        {/* Expanded detail */}
        {selected && (
          <div className="mt-4 p-4 bg-surface-2 rounded-lg border border-border-bright">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-semibold text-text-primary">{selected.label}</h4>
              <button
                onClick={() => setSelectedId(null)}
                className="text-xs text-text-muted hover:text-text-secondary cursor-pointer bg-transparent border-none"
              >
                Close
              </button>
            </div>

            {/* Side by side comparison */}
            <div className="grid grid-cols-2 gap-3 mb-3">
              <div>
                <div className="text-[10px] text-text-muted uppercase tracking-wider mb-1">Source</div>
                <div className="aspect-video bg-surface-0 rounded-lg border border-border overflow-hidden">
                  {sourceVideoUrl ? (
                    <video src={sourceVideoUrl} className="w-full h-full object-cover" controls muted playsInline />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-xs text-text-muted">No source video</div>
                  )}
                </div>
              </div>
              <div>
                <div className="text-[10px] text-text-muted uppercase tracking-wider mb-1">Generated</div>
                <div className="aspect-video bg-surface-0 rounded-lg border border-border overflow-hidden">
                  {selected.video_url ? (
                    <video src={selected.video_url} className="w-full h-full object-cover" controls muted playsInline />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-xs text-text-muted">No video yet</div>
                  )}
                </div>
              </div>
            </div>

            {/* Prompt */}
            <div className="mb-3">
              <div className="text-[10px] text-text-muted uppercase tracking-wider mb-1">Prompt</div>
              <p className="text-sm text-text-secondary bg-surface-0 rounded-lg border border-border p-3">
                {selected.prompt}
              </p>
            </div>

            {/* Constraints */}
            <div>
              <div className="text-[10px] text-text-muted uppercase tracking-wider mb-1">Constraints</div>
              <div className="flex flex-wrap gap-1.5">
                {selected.constraints.map((c, i) => (
                  <span key={i} className="text-xs px-2 py-1 rounded bg-surface-3 border border-border/50 text-text-muted">
                    {c}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

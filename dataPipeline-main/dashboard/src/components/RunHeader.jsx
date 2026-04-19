const statusColors = {
  complete: 'bg-accent-green/20 text-accent-green',
  processing: 'bg-accent-amber/20 text-accent-amber',
  failed: 'bg-accent-red/20 text-accent-red',
};

export default function RunHeader({ run, pipeline }) {
  const stages = ['source_video', 'detection', 'tracking', 'annotations', 'world_model', 'synthetic_outputs'];

  return (
    <header className="border-b border-border bg-surface-1 px-5 py-2.5 flex items-center gap-6 shrink-0">
      <div className="flex items-center gap-3">
        <h1 className="text-sm font-semibold text-text-primary tracking-tight">{run.name}</h1>
        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${statusColors[run.status] || statusColors.complete}`}>
          {run.status}
        </span>
      </div>

      <div className="flex items-center gap-4 text-xs text-text-secondary">
        <span>Target: <span className="text-text-primary font-medium">{run.target_object}</span></span>
        <span>Action: <span className="text-text-primary font-medium">{run.action_label}</span></span>
        <span className="text-text-muted">{(run.summary.duration_ms / 1000).toFixed(1)}s</span>
      </div>

      {/* Pipeline progress dots */}
      <div className="flex items-center gap-1 ml-auto">
        {stages.map((key) => {
          const ok = pipeline.stage_status[key] === 'complete';
          return (
            <div
              key={key}
              className={`w-2 h-2 rounded-full ${ok ? 'bg-accent-green' : 'bg-border'}`}
              title={key.replace(/_/g, ' ')}
            />
          );
        })}
      </div>

      <div className="text-xs text-text-muted">
        {run.summary.tracked_object_count} tracked  ·  {run.summary.synthetic_output_count} synthetic
      </div>
    </header>
  );
}

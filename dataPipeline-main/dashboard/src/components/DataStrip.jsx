import { useState } from 'react';

const PHASE_COLORS = {
  idle: '#5c5c6e', reach: '#35d0ff', grasp: '#ffb347',
  lift_and_move: '#7cf29a', place: '#ff6b6b',
};

export default function DataStrip({
  pipeline,
  overlays,
  currentPhase,
  currentRelations,
  worldModel,
  currentTimeMs,
}) {
  const [expanded, setExpanded] = useState(null); // null | 'objects' | 'relations' | 'world_model' | 'json'

  const phaseColor = PHASE_COLORS[currentPhase?.phase] || '#5c5c6e';

  return (
    <div className="bg-surface-1 rounded-lg border border-border shrink-0">
      {/* Compact bar */}
      <div className="flex items-center gap-4 px-4 py-2">
        {/* Current phase */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-text-muted uppercase tracking-wider">Phase</span>
          <span
            className="text-xs font-semibold px-2 py-0.5 rounded-full"
            style={{ backgroundColor: phaseColor + '20', color: phaseColor }}
          >
            {currentPhase?.phase?.replace(/_/g, ' ') || '—'}
          </span>
        </div>

        <div className="w-px h-4 bg-border" />

        {/* Objects */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-text-muted uppercase tracking-wider">Objects</span>
          {overlays.filter(o => o.frame?.visible).map((o) => (
            <span key={o.track_id} className="flex items-center gap-1 text-xs">
              <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: o.color }} />
              <span style={{ color: o.color }}>{o.label}</span>
              <span className="text-text-muted font-mono text-[10px]">
                {o.frame?.confidence ? `${(o.frame.confidence * 100).toFixed(0)}%` : ''}
              </span>
            </span>
          ))}
        </div>

        <div className="w-px h-4 bg-border" />

        {/* Relations */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-text-muted uppercase tracking-wider">Relations</span>
          {currentRelations.length === 0 ? (
            <span className="text-xs text-text-muted/50">none</span>
          ) : (
            currentRelations.map((rel, i) => (
              <span key={i} className="text-xs">
                <span className="text-accent-cyan">{rel.subject}</span>
                <span className="text-text-muted mx-1">{rel.relation}</span>
                <span className="text-accent-green">{rel.object}</span>
              </span>
            ))
          )}
        </div>

        <div className="w-px h-4 bg-border" />

        {/* World model summary */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-text-muted uppercase tracking-wider">World Model</span>
          <span className="text-xs text-text-secondary">
            {worldModel.objects.length} objects · {worldModel.actions.length} phases · {worldModel.relations.length} relations
          </span>
        </div>

        {/* Expand toggles */}
        <div className="ml-auto flex items-center gap-1">
          {['objects', 'relations', 'world_model', 'json'].map((key) => (
            <button
              key={key}
              onClick={() => setExpanded(expanded === key ? null : key)}
              className={`text-[10px] px-2 py-1 rounded border cursor-pointer transition-colors ${
                expanded === key
                  ? 'bg-accent-cyan/15 border-accent-cyan/30 text-accent-cyan'
                  : 'bg-surface-2 border-border text-text-muted hover:text-text-secondary'
              }`}
            >
              {key === 'world_model' ? 'WM' : key === 'json' ? 'JSON' : key.charAt(0).toUpperCase() + key.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Expanded panel */}
      {expanded && (
        <div className="border-t border-border px-4 py-3 max-h-48 overflow-y-auto">
          {expanded === 'objects' && (
            <div className="grid grid-cols-3 gap-2">
              {pipeline.detected_objects.map((obj) => {
                const ov = overlays?.find((o) => o.track_id === obj.track_id);
                return (
                  <div key={obj.track_id} className="flex items-center gap-2 p-2 bg-surface-2 rounded border border-border/50">
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: obj.color }} />
                    <span className="text-xs font-medium text-text-primary">{obj.label}</span>
                    <span className="text-[10px] text-text-muted">{obj.type.replace(/_/g, ' ')}</span>
                    {ov?.frame?.confidence != null && (
                      <span className="text-[10px] font-mono text-text-muted ml-auto">{(ov.frame.confidence * 100).toFixed(0)}%</span>
                    )}
                    {ov?.frame?.bbox && (
                      <span className="text-[10px] font-mono text-text-muted">[{ov.frame.bbox.join(',')}]</span>
                    )}
                  </div>
                );
              })}
            </div>
          )}
          {expanded === 'relations' && (
            <div className="space-y-1.5">
              {worldModel.relations.map((rel, i) => {
                const active = currentTimeMs >= rel.t_start_ms && currentTimeMs < rel.t_end_ms;
                return (
                  <div key={i} className={`flex items-center gap-2 p-2 rounded border text-xs ${
                    active ? 'bg-surface-2 border-border-bright' : 'bg-surface-2/40 border-border/30 opacity-50'
                  }`}>
                    <span className="text-accent-cyan font-medium">{rel.subject}</span>
                    <span className="px-1.5 py-0.5 bg-surface-3 rounded text-text-muted text-[10px]">{rel.relation}</span>
                    <span className="text-accent-green font-medium">{rel.object}</span>
                    <span className="text-[10px] font-mono text-text-muted ml-auto">{(rel.t_start_ms/1000).toFixed(1)}s - {(rel.t_end_ms/1000).toFixed(1)}s</span>
                    {active && <span className="text-[10px] text-accent-cyan">ACTIVE</span>}
                  </div>
                );
              })}
            </div>
          )}
          {expanded === 'world_model' && (
            <div className="grid grid-cols-4 gap-2">
              <Card label="Target" value={worldModel.target_object} />
              <Card label="Action" value={worldModel.action_label} />
              <Card label="Duration" value={`${(worldModel.duration_ms/1000).toFixed(1)}s`} />
              <Card label="Objects" value={worldModel.objects.length} />
              {worldModel.objects.map((obj) => (
                <div key={obj.id} className="flex items-center gap-2 p-2 bg-surface-2 rounded border border-border/50">
                  <span className="text-xs text-text-primary">{obj.label}</span>
                  <span className="text-[10px] px-1.5 py-0.5 bg-surface-3 rounded text-text-muted">{obj.role}</span>
                </div>
              ))}
            </div>
          )}
          {expanded === 'json' && (
            <pre className="text-[10px] font-mono text-text-secondary bg-surface-0 rounded border border-border p-3 overflow-auto max-h-40">
              {JSON.stringify(worldModel, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

function Card({ label, value }) {
  return (
    <div className="p-2 bg-surface-2 rounded border border-border/50">
      <div className="text-[9px] text-text-muted uppercase tracking-wider">{label}</div>
      <div className="text-xs font-semibold text-text-primary mt-0.5">{value}</div>
    </div>
  );
}

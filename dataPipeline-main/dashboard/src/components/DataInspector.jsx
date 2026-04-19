import { useState } from 'react';

const tabs = [
  { id: 'objects', label: 'Objects' },
  { id: 'actions', label: 'Actions' },
  { id: 'relations', label: 'Relations' },
  { id: 'world_model', label: 'World Model' },
  { id: 'raw_json', label: 'Raw JSON' },
];

export default function DataInspector({
  pipeline,
  overlays,
  currentPhase,
  currentRelations,
  worldModel,
  currentTimeMs,
}) {
  const [activeTab, setActiveTab] = useState('objects');

  return (
    <div className="bg-surface-1 rounded-xl border border-border overflow-hidden flex flex-col">
      {/* Tab bar */}
      <div className="flex border-b border-border bg-surface-2/50 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2.5 text-xs font-medium transition-colors whitespace-nowrap border-none outline-none cursor-pointer ${
              activeTab === tab.id
                ? 'text-accent-cyan border-b-2 border-b-accent-cyan bg-surface-1'
                : 'text-text-muted hover:text-text-secondary bg-transparent'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="p-4 flex-1 overflow-y-auto max-h-[400px]">
        {activeTab === 'objects' && (
          <ObjectsPanel pipeline={pipeline} overlays={overlays} />
        )}
        {activeTab === 'actions' && (
          <ActionsPanel worldModel={worldModel} currentPhase={currentPhase} currentTimeMs={currentTimeMs} />
        )}
        {activeTab === 'relations' && (
          <RelationsPanel currentRelations={currentRelations} worldModel={worldModel} currentTimeMs={currentTimeMs} />
        )}
        {activeTab === 'world_model' && (
          <WorldModelPanel worldModel={worldModel} />
        )}
        {activeTab === 'raw_json' && (
          <RawJsonPanel worldModel={worldModel} pipeline={pipeline} />
        )}
      </div>
    </div>
  );
}

function ObjectsPanel({ pipeline, overlays }) {
  return (
    <div className="space-y-3">
      <div className="text-xs text-text-muted mb-2">
        {pipeline.detected_objects.length} objects detected
      </div>
      {pipeline.detected_objects.map((obj) => {
        const overlay = overlays?.find((o) => o.track_id === obj.track_id);
        const conf = overlay?.frame?.confidence;
        return (
          <div
            key={obj.track_id}
            className="flex items-center gap-3 p-3 bg-surface-2 rounded-lg border border-border/50"
          >
            <div className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: obj.color }} />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-text-primary">{obj.label}</div>
              <div className="text-xs text-text-muted">{obj.type.replace(/_/g, ' ')}</div>
            </div>
            {conf != null && (
              <div className="text-right">
                <div className="text-sm font-mono text-text-primary">{(conf * 100).toFixed(0)}%</div>
                <div className="w-16 h-1 bg-surface-3 rounded-full mt-1 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${conf * 100}%`,
                      backgroundColor: conf > 0.9 ? '#7cf29a' : conf > 0.8 ? '#ffb347' : '#ff6b6b',
                    }}
                  />
                </div>
              </div>
            )}
            {overlay?.frame?.bbox && (
              <div className="text-xs font-mono text-text-muted">
                [{overlay.frame.bbox.join(', ')}]
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function ActionsPanel({ worldModel, currentPhase, currentTimeMs }) {
  const PHASE_COLORS = {
    idle: '#5c5c6e', reach: '#35d0ff', grasp: '#ffb347',
    lift_and_move: '#7cf29a', place: '#ff6b6b',
  };

  return (
    <div className="space-y-2">
      <div className="text-xs text-text-muted mb-2">
        {worldModel.actions.length} action phases
      </div>
      {worldModel.actions.map((action) => {
        const isActive = currentTimeMs >= action.t_start_ms && currentTimeMs < action.t_end_ms;
        const color = PHASE_COLORS[action.phase] || '#5c5c6e';
        const duration = action.t_end_ms - action.t_start_ms;
        return (
          <div
            key={action.phase + action.t_start_ms}
            className={`flex items-center gap-3 p-3 rounded-lg border transition-colors ${
              isActive
                ? 'bg-surface-2 border-border-bright'
                : 'bg-surface-2/50 border-border/30'
            }`}
          >
            <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: color }} />
            <div className="flex-1">
              <div className="text-sm font-medium" style={{ color: isActive ? color : 'var(--color-text-primary)' }}>
                {action.phase.replace(/_/g, ' ')}
                {isActive && <span className="ml-2 text-[10px] opacity-60">ACTIVE</span>}
              </div>
            </div>
            <div className="text-xs font-mono text-text-muted">
              {(action.t_start_ms / 1000).toFixed(1)}s – {(action.t_end_ms / 1000).toFixed(1)}s
            </div>
            <div className="text-xs text-text-muted">
              {(duration / 1000).toFixed(1)}s
            </div>
          </div>
        );
      })}
    </div>
  );
}

function RelationsPanel({ currentRelations, worldModel, currentTimeMs }) {
  return (
    <div className="space-y-4">
      {/* Current relations */}
      <div>
        <div className="text-xs text-text-muted mb-2">
          Active at {(currentTimeMs / 1000).toFixed(1)}s
        </div>
        {currentRelations.length === 0 ? (
          <div className="text-sm text-text-muted/60 p-3 bg-surface-2 rounded-lg border border-border/30">
            No active relations
          </div>
        ) : (
          <div className="space-y-2">
            {currentRelations.map((rel, i) => (
              <div key={i} className="flex items-center gap-2 p-3 bg-surface-2 rounded-lg border border-border/50">
                <span className="text-sm font-medium text-accent-cyan">{rel.subject}</span>
                <span className="text-xs px-2 py-0.5 rounded bg-surface-3 text-text-secondary">{rel.relation}</span>
                <span className="text-sm font-medium text-accent-green">{rel.object}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* All relations */}
      <div>
        <div className="text-xs text-text-muted mb-2">All relations</div>
        <div className="space-y-2">
          {worldModel.relations.map((rel, i) => {
            const isActive = currentTimeMs >= rel.t_start_ms && currentTimeMs < rel.t_end_ms;
            return (
              <div key={i} className={`flex items-center gap-2 p-3 rounded-lg border ${
                isActive ? 'bg-surface-2 border-border-bright' : 'bg-surface-2/50 border-border/30'
              }`}>
                <span className="text-sm font-medium text-accent-cyan">{rel.subject}</span>
                <span className="text-xs px-2 py-0.5 rounded bg-surface-3 text-text-secondary">{rel.relation}</span>
                <span className="text-sm font-medium text-accent-green">{rel.object}</span>
                <span className="text-xs font-mono text-text-muted ml-auto">
                  {(rel.t_start_ms / 1000).toFixed(1)}s – {(rel.t_end_ms / 1000).toFixed(1)}s
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function WorldModelPanel({ worldModel }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <InfoCard label="Target Object" value={worldModel.target_object} />
        <InfoCard label="Action" value={worldModel.action_label} />
        <InfoCard label="Duration" value={`${(worldModel.duration_ms / 1000).toFixed(1)}s`} />
        <InfoCard label="Objects" value={worldModel.objects.length} />
      </div>

      <div>
        <div className="text-xs text-text-muted mb-2">Scene Objects</div>
        <div className="space-y-2">
          {worldModel.objects.map((obj) => (
            <div key={obj.id} className="flex items-center gap-3 p-2.5 bg-surface-2 rounded-lg border border-border/50">
              <div className="text-sm font-medium text-text-primary">{obj.label}</div>
              <span className="text-xs px-2 py-0.5 rounded bg-surface-3 text-text-muted">{obj.role}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function RawJsonPanel({ worldModel, pipeline }) {
  const [view, setView] = useState('world_model');

  const data = view === 'world_model' ? worldModel : pipeline;

  return (
    <div>
      <div className="flex gap-2 mb-3">
        <button
          onClick={() => setView('world_model')}
          className={`text-xs px-3 py-1.5 rounded-lg border transition-colors cursor-pointer ${
            view === 'world_model'
              ? 'bg-accent-cyan/15 border-accent-cyan/30 text-accent-cyan'
              : 'bg-surface-2 border-border text-text-muted hover:text-text-secondary'
          }`}
        >
          World Model
        </button>
        <button
          onClick={() => setView('pipeline')}
          className={`text-xs px-3 py-1.5 rounded-lg border transition-colors cursor-pointer ${
            view === 'pipeline'
              ? 'bg-accent-cyan/15 border-accent-cyan/30 text-accent-cyan'
              : 'bg-surface-2 border-border text-text-muted hover:text-text-secondary'
          }`}
        >
          Pipeline
        </button>
      </div>
      <pre className="text-xs font-mono text-text-secondary bg-surface-0 rounded-lg border border-border p-4 overflow-auto max-h-[300px] whitespace-pre-wrap">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

function InfoCard({ label, value }) {
  return (
    <div className="p-3 bg-surface-2 rounded-lg border border-border/50">
      <div className="text-[10px] text-text-muted uppercase tracking-wider">{label}</div>
      <div className="text-sm font-semibold text-text-primary mt-0.5">{value}</div>
    </div>
  );
}

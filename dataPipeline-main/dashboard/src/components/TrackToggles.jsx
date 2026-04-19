export default function TrackToggles({ detectedObjects, visibleTracks, onToggle }) {
  return (
    <div className="bg-surface-1 rounded-xl border border-border p-4">
      <h3 className="text-sm font-semibold text-text-primary mb-3">Track Visibility</h3>
      <div className="flex flex-wrap gap-2">
        {detectedObjects.map((obj) => {
          const isVisible = visibleTracks[obj.track_id];
          return (
            <button
              key={obj.track_id}
              onClick={() => onToggle(obj.track_id)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all cursor-pointer ${
                isVisible
                  ? 'bg-opacity-20 border-opacity-40'
                  : 'bg-surface-2 border-border text-text-muted opacity-50'
              }`}
              style={isVisible ? {
                backgroundColor: obj.color + '20',
                borderColor: obj.color + '40',
                color: obj.color,
              } : {}}
            >
              <div
                className={`w-2 h-2 rounded-full transition-opacity ${isVisible ? 'opacity-100' : 'opacity-30'}`}
                style={{ backgroundColor: obj.color }}
              />
              {obj.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

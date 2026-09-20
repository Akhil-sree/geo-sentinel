interface MapControlsProps {
  is3D: boolean;
  onToggle2D: () => void;
  onToggle3D: () => void;
  onResetView: () => void;
}

export default function MapControls({ is3D, onToggle2D, onToggle3D, onResetView }: MapControlsProps) {
  return (
    <div className="leaflet-top leaflet-right">
      <div className="m-3 flex flex-col gap-2">
        {/* 2D/3D Toggle */}
        <div id="view-toggle" className="flex overflow-hidden rounded-md" style={{
          background: 'rgba(6, 22, 17, 0.72)',
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          border: '1px solid rgba(255,255,255,0.12)',
          boxShadow: '0 2px 10px rgba(0,0,0,0.25)',
        }}>
          <button id="btn-2d" onClick={onToggle2D} className={`view-btn ${!is3D ? "active" : ""}`}>
            2D
          </button>
          <button id="btn-3d" onClick={onToggle3D} className={`view-btn ${is3D ? "active" : ""}`} title="Visual tilt only — not real 3D terrain" aria-label="Tilted view (visual tilt only, not 3D terrain)">
            3D⋆ tilt
          </button>
        </div>

        {/* Reset View */}
        <button onClick={onResetView}
          className="rounded-lg px-3 py-2 text-[12px] font-semibold text-gs-text transition-colors"
          style={{
          background: 'rgba(238, 241, 235, 0.86)',
          backdropFilter: 'blur(4px)',
          WebkitBackdropFilter: 'blur(4px)',
          border: '1px solid rgba(255, 255, 255, 0.28)',
          boxShadow: '0 2px 8px rgba(15, 35, 27, 0.06)',
        }}
        onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(250, 251, 248, 0.94)'; }}
        onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(238, 241, 235, 0.86)'; }}
        >
          ⌂ Meghalaya
        </button>
      </div>
    </div>
  );
}

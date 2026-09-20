import { useEffect, useState } from "react";
import L from "leaflet";
import { useDraggable } from "../../hooks/useDraggable";

/** Compact floating legend with grouped categories — risk, zones, roads.
 *  Roads use visual hierarchy matching the actual road network rendering. */
export default function MapLegend() {
  const [open, setOpen] = useState(true);
  const drag = useDraggable("map-legend");

  useEffect(() => {
    const el = drag.ref.current;
    if (!el) return;
    L.DomEvent.disableClickPropagation(el);
    L.DomEvent.disableScrollPropagation(el);
  }, [drag.ref]);

  const RISK_LEVELS = [
    { label: "Critical", color: "#B4232B" },
    { label: "High", color: "#E76016" },
    { label: "Moderate", color: "#D19217" },
    { label: "Low", color: "#2563EB" },
  ];

  const ZONE_STATES = [
    { label: "Critical", color: "#B4232B" },
    { label: "Degrading", color: "#E76016" },
    { label: "Stressed", color: "#D19217" },
    { label: "Stable", color: "#2563EB" },
  ];

  return (
    <div ref={drag.ref} style={{ position: "absolute", bottom: 12, left: 12, zIndex: 999, ...drag.style }}>
      <div className="gs-geo-context" style={{ width: 160, padding: 0 }}>
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          {...drag.handleProps}
          className="flex w-full items-center justify-between px-3 py-2"
          style={{ borderBottom: open ? '1px solid rgba(230,230,230,0.6)' : 'none', ...drag.handleProps.style }}
        >
          <span className="gs-label" style={{ color: '#075240' }}>Legend</span>
          <span className="flex items-center gap-1">
            <span className="text-[10px] text-gs-text-secondary/50" aria-hidden>⠿</span>
            <span className="text-[10px] text-gs-text-secondary" aria-hidden>{open ? "▾" : "▸"}</span>
          </span>
        </button>
        {open && (
          <div className="px-3 py-2">
            {/* Risk levels */}
            <div className="gs-label mb-1" style={{ color: '#5F6B62', fontSize: 9 }}>RISK</div>
            {RISK_LEVELS.map((s) => (
              <div key={s.label} className="flex items-center gap-1.5 py-px">
                <i className="shrink-0 rounded-full" style={{ width: 7, height: 7, background: s.color }} aria-hidden />
                <span className="text-[10.5px] font-medium text-gs-text">{s.label}</span>
              </div>
            ))}

            {/* Zone states */}
            <div className="gs-section-rule my-1.5" />
            <div className="gs-label mb-1" style={{ color: '#5F6B62', fontSize: 9 }}>ZONES</div>
            {ZONE_STATES.map((s) => (
              <div key={s.label} className="flex items-center gap-1.5 py-px">
                <svg width="12" height="9" viewBox="0 0 12 9" aria-hidden>
                  <rect x="1" y="1" width="10" height="7" rx="1.5" fill={`${s.color}22`} stroke={s.color} strokeWidth="1.2" />
                </svg>
                <span className="text-[10.5px] font-medium text-gs-text">{s.label}</span>
              </div>
            ))}

            {/* Road hierarchy */}
            <div className="gs-section-rule my-1.5" />
            <div className="gs-label mb-1" style={{ color: '#5F6B62', fontSize: 9 }}>ROADS</div>
            <div className="flex items-center gap-1.5 py-px">
              <i className="inline-block h-[2.5px] w-4 shrink-0 rounded-full" style={{ background: "#4A5E4D" }} aria-hidden />
              <span className="text-[10.5px] font-medium text-gs-text">━━ Major</span>
            </div>
            <div className="flex items-center gap-1.5 py-px">
              <i className="inline-block h-[2px] w-4 shrink-0 rounded-full" style={{ background: "#6B806E" }} aria-hidden />
              <span className="text-[10.5px] font-medium text-gs-text">── Secondary</span>
            </div>
            <div className="flex items-center gap-1.5 py-px">
              <i className="inline-block h-[1.5px] w-4 shrink-0 rounded-full" style={{ background: "#8A9A8D" }} aria-hidden />
              <span className="text-[10.5px] font-medium text-gs-text">┄┄ Local</span>
            </div>
            <div className="flex items-center gap-1.5 py-px">
              <i className="inline-block h-[1px] w-4 shrink-0" style={{ borderTop: "1px dashed #B5C0B8" }} aria-hidden />
              <span className="text-[10.5px] font-medium text-gs-text">··· Minor</span>
            </div>

            {/* Safety */}
            <div className="gs-section-rule my-1.5" />
            <div className="gs-label mb-1" style={{ color: '#5F6B62', fontSize: 9 }}>SAFETY</div>
            <div className="flex items-center gap-1.5 py-px">
              <i className="shrink-0 rounded-full" style={{ width: 7, height: 7, background: "#3B82F6", opacity: 0.5, border: "1px solid #2563EB" }} aria-hidden />
              <span className="text-[10.5px] font-medium text-gs-text">Safe / stable zone</span>
            </div>
            <div className="flex items-center gap-1.5 py-px">
              <i className="inline-block h-[2.5px] w-4 shrink-0 rounded-full" style={{ background: "#1D4ED8" }} aria-hidden />
              <span className="text-[10.5px] font-medium text-gs-text">━━ Rescue route</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

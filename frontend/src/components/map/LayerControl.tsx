import { useEffect, useState } from "react";
import L from "leaflet";
import { useDraggable } from "../../hooks/useDraggable";

export interface MapLayers {
  zones: boolean;
  hotspots: boolean;
  threats: boolean;
  roads: boolean;
  heat: boolean;
  reports: boolean;
  safeZones: boolean;
  rescueRoute: boolean;
}

export interface RoadCategoryFilters {
  major: boolean;
  secondary: boolean;
  local: boolean;
  minor: boolean;
}

export const DEFAULT_ROAD_FILTERS: RoadCategoryFilters = {
  major: true,
  secondary: true,
  local: true,
  minor: true,
};

const ROAD_CATEGORY_ITEMS: { key: keyof RoadCategoryFilters; label: string; hint: string }[] = [
  { key: "major", label: "Major", hint: "Highways and primary roads" },
  { key: "secondary", label: "Secondary", hint: "State and district roads" },
  { key: "local", label: "Local", hint: "Village and access roads" },
  { key: "minor", label: "Minor", hint: "Tracks and paths" },
];

export const DEFAULT_LAYERS: MapLayers = {
  zones: true,
  hotspots: true,
  threats: true,
  roads: true,
  heat: true,
  reports: true,
  safeZones: true,
  rescueRoute: true,
};

const LAYER_GROUPS = [
  {
    title: "Hazard",
    items: [
      { key: "zones" as const, label: "Risk zones", hint: "Zone grids colored by slope state" },
      { key: "hotspots" as const, label: "Hotspots", hint: "Derived detection points" },
      { key: "threats" as const, label: "Threat markers", hint: "Top zones by backend risk" },
      { key: "heat" as const, label: "Risk intensity", hint: "Heat overlay from zone scores" },
    ],
  },
  {
    title: "Infrastructure",
    items: [
      { key: "roads" as const, label: "OSM roads", hint: "Real OSM road geometry from PBF" },
    ],
  },
  {
    title: "Context",
    items: [
      { key: "reports" as const, label: "Field reports", hint: "Citizen reports awaiting validation" },
    ],
  },
  {
    title: "Safety",
    items: [
      { key: "safeZones" as const, label: "Safe / stable zones", hint: "Safe zones" },
      { key: "rescueRoute" as const, label: "Rescue route", hint: "Active rescue route overlay" },
    ],
  },
];

/** Layer control — professional GIS grouping with road filter. */
export default function LayerControl({
  layers,
  onToggle,
  roadFilters,
  onRoadFilterToggle,
}: {
  layers: MapLayers;
  onToggle: (key: keyof MapLayers) => void;
  roadFilters?: RoadCategoryFilters;
  onRoadFilterToggle?: (key: keyof RoadCategoryFilters) => void;
}) {
  const [open, setOpen] = useState(true);
  const drag = useDraggable("map-layers");

  useEffect(() => {
    const el = drag.ref.current;
    if (!el) return;
    L.DomEvent.disableClickPropagation(el);
    L.DomEvent.disableScrollPropagation(el);
  }, [drag.ref]);

  return (
    <div ref={drag.ref} style={{ position: "absolute", top: 138, right: 12, zIndex: 999, ...drag.style }}>
      <div className="gs-geo-context" style={{ width: 180, padding: 0 }}>
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          {...drag.handleProps}
          className="flex w-full items-center justify-between px-3 py-2"
          style={{ borderBottom: open ? '1px solid rgba(230,230,230,0.6)' : 'none', ...drag.handleProps.style }}
        >
          <span className="gs-label" style={{ color: '#075240' }}>Map Layers</span>
          <span className="flex items-center gap-1">
            <span className="text-[10px] text-gs-text-secondary/50" aria-hidden>⠿</span>
            <span className="text-[10px] text-gs-text-secondary" aria-hidden>{open ? "▾" : "▸"}</span>
          </span>
        </button>
        {open && (
          <div className="px-3 py-2">
            {LAYER_GROUPS.map((group) => (
              <div key={group.title} className="mb-2 last:mb-0">
                <div className="gs-label mb-1" style={{ color: '#5F6B62', fontSize: 9 }}>
                  {group.title.toUpperCase()}
                </div>
                <ul className="space-y-0.5">
                  {group.items.map((it) => (
                    <li key={it.key}>
                      <label className="flex cursor-pointer items-center gap-2 py-0.5" title={it.hint}>
                        <input
                          type="checkbox"
                          checked={layers[it.key]}
                          onChange={() => onToggle(it.key)}
                          className="h-3 w-3 accent-[#1A3C2E]"
                        />
                        <span className="text-[11px] font-medium text-gs-text">{it.label}</span>
                      </label>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
            {roadFilters && onRoadFilterToggle && layers.roads && (
              <div className="mb-2 last:mb-0">
                <div className="gs-label mb-1" style={{ color: '#5F6B62', fontSize: 9 }}>
                  ROAD CLASS
                </div>
                <ul className="space-y-0.5">
                  {ROAD_CATEGORY_ITEMS.map((it) => (
                    <li key={it.key}>
                      <label className="flex cursor-pointer items-center gap-2 py-0.5" title={it.hint}>
                        <input
                          type="checkbox"
                          checked={roadFilters[it.key]}
                          onChange={() => onRoadFilterToggle(it.key)}
                          className="h-3 w-3 accent-[#1A3C2E]"
                        />
                        <span className="text-[11px] font-medium text-gs-text">{it.label}</span>
                      </label>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

import { useEffect, useRef, useMemo, useState, useCallback } from "react";
import { MapContainer, useMap, useMapEvents } from "react-leaflet";
import BasemapLayer from "./BasemapLayer";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.heat";
import MapLegend from "./MapLegend";
import MapControls from "./MapControls";
import LayerControl, { DEFAULT_LAYERS, DEFAULT_ROAD_FILTERS, type MapLayers, type RoadCategoryFilters } from "./LayerControl";
import RoadNetworkLayer from "./RoadNetworkLayer";
import SafeZoneLayer from "./SafeZoneLayer";
import RescueRouteLayer from "./RescueRouteLayer";
import RescueChip from "./RescueChip";
import HotspotMarker from "./HotspotMarker";
import SimulationOverlay from "./SimulationOverlay";
import MapHoverCard from "./MapHoverCard";
import ThreatMarker from "./ThreatMarker";
import { useUIStore } from "../../store/uiStore";
import { haversineKm, generateHotspotCoords } from "../../lib/geo";
import { fmtMmOpt } from "../../lib/format";
import { consumePolygonClick } from "../../lib/clickFlag";
import { useDraggable } from "../../hooks/useDraggable";
import { getBlockedRoads } from "../../api/dashboard";
import ZonePolygon from "./ZonePolygon";
import { ReportMarker } from "./ReportMarker";
import type { Zone } from "../../types/zone";
import type { ZoneRisk, IntensificationResult, SimulationResult } from "../../types/risk";
import type { RoadFeature } from "../../api/dashboard";

const CENTER: [number, number] = [25.45, 91.1];

export interface ThreatZone {
  id: number;
  zoneId: string;
  name: string;
  district: string;
  lat: number;
  lng: number;
  risk: "critical" | "high" | "moderate" | "low";
  score: number | null;
  rainfall: string;
  soilMoisture: string;
  slopeStress: string;
  trend: string;
}

function severityToRisk(sev: string): ThreatZone["risk"] {
  if (sev === "VERY_HIGH") return "critical";
  if (sev === "HIGH") return "high";
  if (sev === "MODERATE") return "moderate";
  return "low";
}

function soilLabel(sm: number | null | undefined): string {
  if (typeof sm !== "number" || !Number.isFinite(sm)) return "—";
  return sm > 0.45 ? "Saturated" : sm > 0.3 ? "Elevated" : "Normal";
}

/* ── Tile contrast filter ── */
function TileContrastFilter() {
  const map = useMap();
  useEffect(() => {
    const apply = () => {
      const panes = map.getContainer().querySelectorAll(".leaflet-tile-pane");
      panes.forEach((pane) => {
        (pane as HTMLElement).style.filter = "contrast(1.08) saturate(1.08) brightness(0.92)";
      });
    };
    apply();
    map.on("load", apply);
    return () => { map.off("load", apply); };
  }, [map]);
  return null;
}

/* ── Map click handler ── */
function MapClickHandler({ zones }: { zones: Zone[] }) {
  const selectZone = useUIStore((s) => s.selectZone);
  useMapEvents({
    click(e) {
      if (consumePolygonClick()) return;
      if (zones.length === 0) return;
      const { lat, lng } = e.latlng;
      let nearest = zones[0];
      let minDist = Infinity;
      for (const z of zones) {
        const d = haversineKm({ lat, lng }, { lat: z.lat, lng: z.lng });
        if (d < minDist) { minDist = d; nearest = z; }
      }
      selectZone(nearest.id);
    },
  });
  return null;
}

/* ── Heatmap ── */
function HeatmapLayer({ risks, zones }: { risks: ZoneRisk[]; zones: Zone[] }) {
  const map = useMap();
  const layerRef = useRef<L.HeatLayer | null>(null);

  useEffect(() => {
    if (layerRef.current) map.removeLayer(layerRef.current);

    const zoneCoords = new Map(zones.map((z) => [z.id, { lat: z.lat, lng: z.lng }]));
    const points: [number, number, number][] = risks.flatMap((r) => {
      const coord = zoneCoords.get(r.zone_id);
      if (!coord) return [];
      const h = [...r.zone_id].reduce((a, c) => ((a * 31 + c.charCodeAt(0)) | 0), 7);
      const frac = (i: number) => {
        const x = Math.sin(h * 127.1 + i * 311.7) * 43758.5453;
        return x - Math.floor(x);
      };
      const intensity = r.slope_stress_score ?? r.risk_score;
      if (typeof intensity !== "number" || intensity < 0.25) return [];
      const spread = r.escalated ? 0.035 : 0.02;
      const pts: [number, number, number][] = [[coord.lat, coord.lng, intensity]];
      const count = r.escalated ? 8 : 4;
      for (let i = 0; i < count; i++) {
        const angle = (Math.PI * 2 * i) / count;
        const dist = spread * (0.3 + frac(i) * 0.7);
        pts.push([
          coord.lat + Math.sin(angle) * dist,
          coord.lng + Math.cos(angle) * dist / Math.cos((coord.lat * Math.PI) / 180),
          intensity * (0.3 + frac(i + 99) * 0.4),
        ]);
      }
      return pts;
    });

    if (points.length === 0) return;
    const heat = L.heatLayer(points, {
      radius: 18, blur: 14, maxZoom: 11, max: 1.0,
      gradient: {
        0.15: "#2563EB", 0.30: "#2563EB", 0.45: "#d97706",
        0.60: "#ea580c", 0.75: "#ba1a1a", 0.90: "#991b1b", 1.0: "#7f1d1d",
      },
    });
    heat.addTo(map);
    layerRef.current = heat;
    return () => { if (layerRef.current) map.removeLayer(layerRef.current); };
  }, [risks, zones, map]);

  return null;
}

/* ── Map view controller ── */
function MapViewController() {
  const map = useMap();
  useEffect(() => { setTimeout(() => map.invalidateSize(), 100); }, [map]);
  return null;
}

/* ── Map padding ── */
function MapPadding() {
  const map = useMap();
  useEffect(() => {
    (map as any).options.paddingTopLeft = [220, 100];
    (map as any).options.paddingBottomRight = [20, 20];
  }, [map]);
  return null;
}

/* ── Hillshade bridge ── */
function MapBridge({ is3D, onFlyToSelected }: { is3D: boolean; onFlyToSelected: React.MutableRefObject<((lat: number, lng: number) => void) | null> }) {
  const map = useMap();
  const hillshadeRef = useRef<L.TileLayer | null>(null);

  useEffect(() => {
    onFlyToSelected.current = (lat: number, lng: number) => {
      map.flyTo([lat, lng], 10, { duration: 0.8 });
    };
    return () => { onFlyToSelected.current = null; };
  }, [map, onFlyToSelected]);

  useEffect(() => {
    if (is3D) {
      if (!hillshadeRef.current) {
        hillshadeRef.current = L.tileLayer(
          "https://server.arcgisonline.com/ArcGIS/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}",
          { maxZoom: 18, opacity: 0.4 }
        );
      }
      hillshadeRef.current.addTo(map);
    } else {
      if (hillshadeRef.current && map.hasLayer(hillshadeRef.current)) {
        map.removeLayer(hillshadeRef.current);
      }
    }
    return () => {
      if (hillshadeRef.current && map.hasLayer(hillshadeRef.current)) {
        map.removeLayer(hillshadeRef.current);
      }
    };
  }, [is3D, map]);

  return null;
}

/* ══════════════════════════════════════════════════════════
   MAP HUD — Coordinate Readout (bottom-left)
   ══════════════════════════════════════════════════════════ */
function CoordinateReadout() {
  const map = useMap();
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onMove = (e: L.LeafletMouseEvent) => {
      setCoords({ lat: e.latlng.lat, lng: e.latlng.lng });
    };
    map.on("mousemove", onMove);
    return () => { map.off("mousemove", onMove); };
  }, [map]);

  useEffect(() => {
    const el = rootRef.current;
    if (!el) return;
    L.DomEvent.disableClickPropagation(el);
    L.DomEvent.disableScrollPropagation(el);
  }, []);

  return (
    <div ref={rootRef} className="gs-map-hud" style={{
      position: "absolute", bottom: 12, left: 12, zIndex: 999, padding: "5px 8px", pointerEvents: "none",
    }}>
      {coords ? (
        <>
          <div style={{ fontSize: 11, fontWeight: 600, color: "rgba(255,255,255,0.9)" }}>
            {coords.lat.toFixed(4)}° N
          </div>
          <div style={{ fontSize: 11, fontWeight: 600, color: "rgba(255,255,255,0.9)" }}>
            {coords.lng.toFixed(4)}° E
          </div>
        </>
      ) : (
        <div style={{ fontSize: 10, color: "rgba(255,255,255,0.4)" }}>Hover map</div>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════
   MAP HUD — Status HUD (top-left)
   ══════════════════════════════════════════════════════════ */
function MapStatusHUD() {
  const map = useMap();
  const [zoom, setZoom] = useState(map.getZoom());
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onZoom = () => setZoom(map.getZoom());
    map.on("zoomend", onZoom);
    return () => { map.off("zoomend", onZoom); };
  }, [map]);

  useEffect(() => {
    const el = rootRef.current;
    if (!el) return;
    L.DomEvent.disableClickPropagation(el);
    L.DomEvent.disableScrollPropagation(el);
  }, []);

  return (
    <div ref={rootRef} className="gs-map-hud" style={{
      position: "absolute", top: 12, left: 12, zIndex: 999, padding: "6px 10px", pointerEvents: "none",
    }}>
      <div className="gs-label-dark" style={{ marginBottom: 4, fontSize: 9 }}>GEO VIEW</div>
      <div style={{ fontSize: 11, fontWeight: 700, color: "rgba(255,255,255,0.9)", letterSpacing: "0.04em" }}>
        MEGHALAYA
      </div>
      <div style={{ fontSize: 10, color: "rgba(255,255,255,0.5)", marginTop: 3 }}>
        ZOOM {zoom.toFixed(1)}
      </div>
      <div style={{ fontSize: 10, color: "rgba(255,255,255,0.5)" }}>
        ROAD NETWORK · OSM
      </div>
      <div style={{ fontSize: 10, color: "rgba(255,255,255,0.5)" }}>
        SATELLITE · ESRI
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════
   MAP HUD — Scale Bar (bottom-center)
   ══════════════════════════════════════════════════════════ */
function ScaleBarHUD() {
  const map = useMap();
  const [scaleText, setScaleText] = useState("10 km");
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const update = () => {
      const zoom = map.getZoom();
      const metersPerPixel = 156543.03392 * Math.cos((25.45 * Math.PI) / 180) / Math.pow(2, zoom);
      const barWidthPx = 120;
      const meters = barWidthPx * metersPerPixel;
      if (meters >= 1000) {
        setScaleText(`${(meters / 1000).toFixed(0)} km`);
      } else {
        setScaleText(`${Math.round(meters)} m`);
      }
    };
    update();
    map.on("zoomend", update);
    return () => { map.off("zoomend", update); };
  }, [map]);

  useEffect(() => {
    const el = rootRef.current;
    if (!el) return;
    L.DomEvent.disableClickPropagation(el);
    L.DomEvent.disableScrollPropagation(el);
  }, []);

  return (
    <div ref={rootRef} className="gs-map-hud" style={{
      position: "absolute", bottom: 12, left: "50%", transform: "translateX(-50%)",
      zIndex: 999, padding: "4px 8px", pointerEvents: "none",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 0 }}>
        <div style={{ width: 120, height: 3, display: "flex" }}>
          <div style={{ flex: 1, background: "rgba(255,255,255,0.6)" }} />
          <div style={{ flex: 1, background: "rgba(255,255,255,0.2)" }} />
          <div style={{ flex: 1, background: "rgba(255,255,255,0.6)" }} />
        </div>
      </div>
      <div style={{ fontSize: 9, color: "rgba(255,255,255,0.6)", textAlign: "center", marginTop: 2 }}>
        {scaleText}
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════
   MAP HUD — North Indicator (top-right, below controls)
   ══════════════════════════════════════════════════════════ */
function NorthIndicator() {
  const rootRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = rootRef.current;
    if (!el) return;
    L.DomEvent.disableClickPropagation(el);
    L.DomEvent.disableScrollPropagation(el);
  }, []);

  return (
    <div ref={rootRef} className="gs-map-hud" style={{
      position: "absolute", top: 12, right: 12, zIndex: 999,
      padding: "4px 8px", pointerEvents: "none", textAlign: "center",
    }}>
      <div className="gs-north">N</div>
      <div style={{
        width: 1, height: 10, background: "rgba(255,255,255,0.4)",
        margin: "2px auto 0",
      }} />
    </div>
  );
}

/* ══════════════════════════════════════════════════════════
   MAP HUD — Geo Context Card (top-left, below status HUD)
   ══════════════════════════════════════════════════════════ */
function GeoContextCard({ zones, roadsActive }: { zones: Zone[]; roadsActive: boolean }) {
  const drag = useDraggable("geo-context");
  useEffect(() => {
    const el = drag.ref.current;
    if (!el) return;
    L.DomEvent.disableClickPropagation(el);
    L.DomEvent.disableScrollPropagation(el);
  }, [drag.ref]);

  return (
    <div ref={drag.ref} className="gs-geo-context" style={{
      position: "absolute", top: 12, left: 12, zIndex: 998,
      padding: "8px 10px", pointerEvents: "none", maxWidth: 180,
      marginTop: 120, ...drag.style,
    }}>
      <div className="flex items-center justify-between" style={{ marginBottom: 4 }}>
        <div className="gs-label" style={{ color: '#075240' }}>Geo Context</div>
        <span {...drag.handleProps} aria-hidden
          style={{ ...drag.handleProps.style, pointerEvents: "auto", color: "rgba(95,107,98,0.5)", fontSize: 10, lineHeight: 1 }}>
          ⠿
        </span>
      </div>
      <div className="space-y-1" style={{ fontSize: 10, color: '#5F6B62' }}>
        <div><strong className="text-gs-text">Meghalaya</strong> · {zones.length} monitored locations</div>
        <div>OSM road network · {roadsActive ? 'Active' : 'Inactive'}</div>
        <div>Satellite basemap · ESRI</div>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════
   Road Info Card (bottom center)
   ══════════════════════════════════════════════════════════ */
function RoadInfoCard({ road, onClose }: { road: RoadFeature; onClose: () => void }) {
  const p = road.properties;
  const rootRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = rootRef.current;
    if (!el) return;
    L.DomEvent.disableClickPropagation(el);
    L.DomEvent.disableScrollPropagation(el);
  }, []);

  const CATEGORY_LABEL: Record<string, string> = {
    major: "Major Road", secondary: "Secondary Road",
    local: "Local Road", minor: "Minor Access",
  };

  return (
    <div ref={rootRef} className="gs-console-dark" style={{
      position: "absolute", bottom: 50, left: "50%", transform: "translateX(-50%)",
      zIndex: 1000, borderRadius: 10, padding: "10px 14px",
      boxShadow: "0 4px 20px rgba(0,0,0,0.35)", minWidth: 220, maxWidth: 340,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: "#E8E6E1" }}>
            {p.name || "Unnamed road"}
          </div>
          <div style={{ fontSize: 11, color: "rgba(255,255,255,0.55)" }}>
            {CATEGORY_LABEL[p.category] || p.category} · {p.highway}{p.ref ? ` · ${p.ref}` : ""}
          </div>
        </div>
        <button onClick={onClose} style={{
          background: "rgba(255,255,255,0.1)", border: "none", color: "rgba(255,255,255,0.6)",
          borderRadius: 4, padding: "2px 6px", cursor: "pointer", fontSize: 12,
        }}>✕</button>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px 12px", fontSize: 11 }}>
        <div style={{ color: "rgba(255,255,255,0.5)" }}>Surface</div>
        <div style={{ color: "#E8E6E1", fontWeight: 600 }}>{p.surface || "Not available"}</div>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════
   Threat HUD — Risk status summary (bottom-right)
   ══════════════════════════════════════════════════════════ */
function ThreatHUD({ hotspots }: { hotspots: ThreatZone[] }) {
  const drag = useDraggable("risk-advisory");
  const counts = useMemo(() => {
    const c: Record<string, number> = { critical: 0, high: 0, moderate: 0, low: 0 };
    hotspots.forEach((h) => { c[h.risk] = (c[h.risk] || 0) + 1; });
    return c;
  }, [hotspots]);

  const rows = [
    { label: "Critical", count: counts.critical, color: "#B91C1C" },
    { label: "High", count: counts.high, color: "#E55A2B" },
    { label: "Moderate", count: counts.moderate, color: "#F2A623" },
    { label: "Low", count: counts.low, color: "#2563EB" },
  ];

  return (
    <div ref={drag.ref} className="gs-geo-context" style={{
      position: "absolute", bottom: 12, right: 12, zIndex: 1000,
      padding: "8px 12px", pointerEvents: "none", ...drag.style,
    }}>
      <div className="flex items-center justify-between" style={{ marginBottom: 6 }}>
        <div className="gs-label" style={{ color: '#075240' }}>
          Risk Status · Advisory
        </div>
        <span {...drag.handleProps} aria-hidden
          style={{ ...drag.handleProps.style, pointerEvents: "auto", color: "rgba(95,107,98,0.5)", fontSize: 10, lineHeight: 1, marginLeft: 8 }}>
          ⠿
        </span>
      </div>
      {rows.map((t) => (
        <div key={t.label} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
          <div style={{ width: 8, height: 8, borderRadius: "50%", background: t.color, flexShrink: 0 }} />
          <span style={{ fontSize: 11, fontWeight: 500, color: "#2D3748", flex: 1 }}>{t.label}</span>
          <span style={{ fontSize: 11, fontWeight: 700, color: t.color, fontFamily: "'IBM Plex Mono', monospace" }}>{t.count}</span>
        </div>
      ))}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════
   MAIN COMPONENT
   ══════════════════════════════════════════════════════════ */

export default function RiskMap({ zones, risks, selectedId, reports, onSelect, intensification, simulationResults, simulationLabel, onClearSimulation, onThreatSelect }: {
  zones: Zone[]; risks: ZoneRisk[]; selectedId: string | null;
  reports: any[]; onSelect: (id: string) => void;
  intensification?: IntensificationResult[];
  simulationResults?: SimulationResult[] | null;
  simulationLabel?: string | null;
  onClearSimulation?: () => void;
  onThreatSelect?: (zone: ThreatZone | null) => void;
}) {
  const selectZone = useUIStore((s) => s.selectZone);
  const [is3D, setIs3D] = useState(false);
  const [layers, setLayers] = useState<MapLayers>(DEFAULT_LAYERS);
  const [roadFilters, setRoadFilters] = useState<RoadCategoryFilters>(DEFAULT_ROAD_FILTERS);
  const mapWrapperRef = useRef<HTMLDivElement>(null);
  const flyToRef = useRef<((lat: number, lng: number) => void) | null>(null);
  const [selectedThreatId, setSelectedThreatId] = useState<number | null>(null);
  const [selectedRoad, setSelectedRoad] = useState<RoadFeature | null>(null);
  const [blockedRoadIds, setBlockedRoadIds] = useState<Set<number>>(new Set());

  const toggleLayer = useCallback(
    (key: keyof MapLayers) => setLayers((l) => ({ ...l, [key]: !l[key] })),
    []
  );

  const toggleRoadFilter = useCallback(
    (key: keyof RoadCategoryFilters) => setRoadFilters((f) => ({ ...f, [key]: !f[key] })),
    []
  );

  // Fetch blocked roads on mount
  useEffect(() => {
    getBlockedRoads()
      .then((data) => setBlockedRoadIds(new Set(data.blocked_road_ids || [])))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedId || !flyToRef.current) return;
    const z = zones.find((zz) => zz.id === selectedId);
    if (z && Number.isFinite(z.lat) && Number.isFinite(z.lng)) {
      flyToRef.current(z.lat, z.lng);
    }
  }, [selectedId, zones]);

  const intMap = useMemo(() => new Map(
    (intensification ?? []).map((i) => [i.zone_id, i])
  ), [intensification]);

  const zoneHotspots = useMemo(() => {
    const map = new Map<string, { lat: number; lng: number }[]>();
    for (const z of zones) {
      const risk = risks.find((r) => r.zone_id === z.id);
      const sev = risk?.severity ?? "LOW";
      map.set(z.id, generateHotspotCoords(z, sev));
    }
    return map;
  }, [zones, risks]);

  const displayRisks = useMemo(() => {
    if (!simulationResults) return risks;
    const simMap = new Map(simulationResults.map((s) => [s.zone_id, s]));
    return risks.map((r) => {
      const s = simMap.get(r.zone_id);
      if (!s) return r;
      return {
        ...r,
        risk_score: s.simulated_risk,
        severity: s.simulated_severity,
        slope_state: s.slope_state as ZoneRisk["slope_state"],
        slope_state_label: s.slope_state_label,
        slope_state_color: s.slope_state_color,
        slope_stress_score: s.simulated_risk,
        escalated: s.escalated,
      };
    });
  }, [risks, simulationResults]);

  const simChangedCount = useMemo(() => {
    if (!simulationResults) return 0;
    return simulationResults.filter((s) => Math.abs(s.simulated_risk - s.current_risk) > 0.02).length;
  }, [simulationResults]);

  const liveThreats = useMemo<ThreatZone[]>(() => {
    const intByZone = new Map((intensification ?? []).map((i) => [i.zone_id, i]));
    return [...risks]
      .sort((a, b) => (b.risk_score ?? -1) - (a.risk_score ?? -1))
      .slice(0, 8)
      .map((r, idx) => {
        const z = zones.find((zz) => zz.id === r.zone_id);
        const inc = intByZone.get(r.zone_id);
        if (z === undefined) return null;
        const stress = r.slope_stress_score ?? r.risk_score;
        return {
          id: idx + 1,
          zoneId: r.zone_id,
          name: r.name,
          district: r.district,
          lat: z.lat,
          lng: z.lng,
          risk: severityToRisk(r.severity),
          score: r.risk_score,
          rainfall: fmtMmOpt(r.rainfall_72h),
          soilMoisture: soilLabel(r.soil_moisture),
          slopeStress: typeof stress === "number" ? `${Math.round(stress * 100)}%` : "—",
          trend: inc && inc.change >= 0.03 ? "escalating" : "stable",
        };
      })
      .filter((x): x is NonNullable<typeof x> => x !== null);
  }, [risks, zones, intensification]);

  const [hotspotHoverRisk, setHotspotHoverRisk] = useState<ZoneRisk | null>(null);
  const [hotspotHoverPos, setHotspotHoverPos] = useState<{ x: number; y: number } | null>(null);
  const [hotspotHoverVisible, setHotspotHoverVisible] = useState(false);
  const [zoneHoverRisk, setZoneHoverRisk] = useState<ZoneRisk | null>(null);
  const [zoneHoverPos, setZoneHoverPos] = useState<{ x: number; y: number } | null>(null);
  const [zoneHoverVisible, setZoneHoverVisible] = useState(false);
  const [zoneHoverCount, setZoneHoverCount] = useState(0);

  const hotspotTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const zoneTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleHotspotHover = useCallback((
    risk: ZoneRisk | null,
    position: { x: number; y: number } | null,
    _index: number,
  ) => {
    if (hotspotTimeoutRef.current) {
      clearTimeout(hotspotTimeoutRef.current);
      hotspotTimeoutRef.current = null;
    }
    if (risk && position) {
      setHotspotHoverRisk(risk);
      setHotspotHoverPos(position);
      setHotspotHoverVisible(true);
    } else {
      hotspotTimeoutRef.current = setTimeout(() => {
        setHotspotHoverVisible(false);
        setHotspotHoverRisk(null);
        setHotspotHoverPos(null);
      }, 150);
    }
  }, []);

  const handleZoneHover = useCallback((
    risk: ZoneRisk | null,
    position: { x: number; y: number } | null,
    count: number,
  ) => {
    if (zoneTimeoutRef.current) {
      clearTimeout(zoneTimeoutRef.current);
      zoneTimeoutRef.current = null;
    }
    if (risk && position) {
      setZoneHoverRisk(risk);
      setZoneHoverPos(position);
      setZoneHoverVisible(true);
      setZoneHoverCount(count);
    } else {
      zoneTimeoutRef.current = setTimeout(() => {
        setZoneHoverVisible(false);
        setZoneHoverRisk(null);
        setZoneHoverPos(null);
        setZoneHoverCount(0);
      }, 150);
    }
  }, []);

  useEffect(() => {
    return () => {
      if (hotspotTimeoutRef.current) clearTimeout(hotspotTimeoutRef.current);
      if (zoneTimeoutRef.current) clearTimeout(zoneTimeoutRef.current);
    };
  }, []);

  useEffect(() => {
    if (selectedId) {
      const z = zones.find((z) => z.id === selectedId);
      if (z && flyToRef.current) {
        flyToRef.current(z.lat, z.lng);
      }
    }
  }, [selectedId, zones]);

  const handleResetView = useCallback(() => {
    if (flyToRef.current) flyToRef.current(25.45, 91.1);
  }, []);

  const handleThreatSelect = useCallback((zone: ThreatZone) => {
    setSelectedThreatId(zone.id);
    selectZone(zone.zoneId);
    onSelect(zone.zoneId);
    onThreatSelect?.(zone);
    if (flyToRef.current) {
      flyToRef.current(zone.lat, zone.lng);
    }
  }, [onThreatSelect, onSelect, selectZone]);

  return (
    <>
      <div ref={mapWrapperRef} className="relative h-full w-full" style={{
        transform: is3D ? "perspective(800px) rotateX(8deg) scale(1.08)" : "none",
        transformOrigin: "center bottom",
        transition: "transform 0.8s ease",
      }}>
        <MapContainer center={CENTER} zoom={8} className="h-full w-full"
                      preferCanvas style={{ background: "#e3e8e1" }}>
          <BasemapLayer />

          <TileContrastFilter />
          <MapBridge is3D={is3D} onFlyToSelected={flyToRef} />
          <MapViewController />
          <MapPadding />
          {layers.heat && <HeatmapLayer risks={displayRisks} zones={zones} />}
          {layers.roads && (
            <RoadNetworkLayer
              selectedRoadId={selectedRoad?.properties.road_id ?? null}
              onRoadSelect={setSelectedRoad}
              roadFilters={roadFilters}
              blockedRoadIds={blockedRoadIds}
            />
          )}
          <MapClickHandler zones={zones} />

          {simulationResults && <SimulationOverlay results={simulationResults} zones={zones} />}

          {layers.zones && zones.map((z) => {
            const risk = displayRisks.find((r) => r.zone_id === z.id);
            const hsCoords = zoneHotspots.get(z.id) ?? [];
            return (
              <ZonePolygon
                key={z.id}
                zone={z}
                risk={risk}
                selected={z.id === selectedId}
                onSelect={(id) => { selectZone(id); onSelect(id); }}
                intensification={intMap.get(z.id) ?? null}
                hotspotCount={hsCoords.length}
                onZoneHover={handleZoneHover}
              />
            );
          })}

          {layers.hotspots && zones.map((z) => {
            const risk = displayRisks.find((r) => r.zone_id === z.id);
            const hsCoords = zoneHotspots.get(z.id) ?? [];
            if (!risk) return null;
            return hsCoords.map((coord, idx) => (
              <HotspotMarker
                key={`hs-${z.id}-${idx}`}
                lat={coord.lat}
                lng={coord.lng}
                risk={risk}
                index={idx}
                selected={z.id === selectedId}
                onHover={handleHotspotHover}
              />
            ));
          })}

          {layers.reports && reports.filter((r) => r.status === "PENDING" || r.status === "VERIFIED")
                  .map((r) => <ReportMarker key={r.id} report={r} />)}

          {layers.safeZones && <SafeZoneLayer visible={layers.safeZones} />}
          {layers.rescueRoute && <RescueRouteLayer visible={layers.rescueRoute} />}

          {layers.threats && liveThreats.map((zone) => (
            <ThreatMarker
              key={`threat-${zone.id}`}
              zone={zone}
              isSelected={selectedThreatId === zone.id}
              onSelect={handleThreatSelect}
            />
          ))}

          <MapLegend />
          <LayerControl layers={layers} onToggle={toggleLayer} roadFilters={roadFilters} onRoadFilterToggle={toggleRoadFilter} />
          <CoordinateReadout />
          <MapStatusHUD />
          <ScaleBarHUD />
          <NorthIndicator />
          <GeoContextCard zones={zones} roadsActive={layers.roads} />
        </MapContainer>

        <MapControls
          is3D={is3D}
          onToggle2D={() => setIs3D(false)}
          onToggle3D={() => setIs3D(true)}
          onResetView={handleResetView}
        />

        {selectedRoad && (
          <RoadInfoCard road={selectedRoad} onClose={() => setSelectedRoad(null)} />
        )}

        {simulationResults && (
          <div style={{
            position: "absolute", top: 12, left: "50%", transform: "translateX(-50%)",
            zIndex: 1000, display: "flex", alignItems: "center", gap: 10,
            background: "rgba(6, 22, 17, 0.85)",
            backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)",
            border: "1px dashed rgba(242, 166, 35, 0.6)",
            borderRadius: 10, padding: "8px 12px",
            boxShadow: "0 2px 12px rgba(0,0,0,0.25)",
          }}>
            <span className="text-[12px] font-semibold" style={{ color: "#F2A623" }}>
              WHAT-IF {simulationLabel ?? "scenario"}
            </span>
            <span className="text-[12px]" style={{ color: "rgba(255,255,255,0.75)" }}>
              {simChangedCount > 0
                ? `${simChangedCount} zone${simChangedCount === 1 ? "" : "s"} changed — map recolored`
                : "≈ current — no zone changed visibly"}
            </span>
            {onClearSimulation && (
              <button
                onClick={onClearSimulation}
                className="rounded-md px-2 py-0.5 text-[12px] font-semibold text-white transition hover:bg-white/20"
                style={{ background: "rgba(255,255,255,0.12)" }}
              >
                ✕ Clear
              </button>
            )}
          </div>
        )}

        <ThreatHUD hotspots={liveThreats} />
        <RescueChip />
      </div>

      <MapHoverCard
        risk={hotspotHoverRisk}
        position={hotspotHoverPos}
        visible={hotspotHoverVisible}
        type="hotspot"
      />

      <MapHoverCard
        risk={zoneHoverRisk}
        position={zoneHoverPos}
        visible={zoneHoverVisible}
        type="zone"
        hotspotCount={zoneHoverCount}
      />
    </>
  );
}

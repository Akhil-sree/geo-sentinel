import { useEffect, useRef, useMemo, useState } from "react";
import { MapContainer, TileLayer, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.heat";
import ZonePolygon from "./ZonePolygon";
import Terrain3DView from "./Terrain3DView";
import { ReportMarker } from "./ReportMarker";
import MapLegend from "./MapLegend";
import MapControls from "./MapControls";
import HotspotMarker from "./HotspotMarker";
import SimulationOverlay from "./SimulationOverlay";
import CellHeatmapLayer from "./CellHeatmapLayer";
import TemporalCellAnimation from "./TemporalCellAnimation";
import { useUIStore } from "../../store/uiStore";
import { haversineKm } from "../../lib/geo";
import { consumePolygonClick } from "../../lib/clickFlag";
import { getRoadSegments, type RoadSegment } from "../../api/dashboard";
import type { Zone } from "../../types/zone";
import type { ZoneRisk, IntensificationResult, Hotspot, SimulationResult } from "../../types/risk";

const CENTER: [number, number] = [25.45, 91.1]; // Meghalaya

export type MapMode = "2d" | "3d";

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

function HeatmapLayer({ risks, zones }: { risks: ZoneRisk[]; zones: Zone[] }) {
  const map = useMap();
  const layerRef = useRef<L.HeatLayer | null>(null);

  useEffect(() => {
    if (layerRef.current) {
      map.removeLayer(layerRef.current);
    }

    const zoneCoords = new Map(zones.map((z) => [z.id, { lat: z.lat, lng: z.lng }]));

    const points: [number, number, number][] = risks.flatMap((r) => {
      const coord = zoneCoords.get(r.zone_id);
      if (!coord) return [];
      const intensity = r.slope_stress_score ?? r.risk_score;
      if (intensity < 0.2) return [];

      const spread = r.escalated ? 0.05 : 0.03;
      const pts: [number, number, number][] = [];

      pts.push([coord.lat, coord.lng, intensity]);

      const count = r.escalated ? 12 : 6;
      for (let i = 0; i < count; i++) {
        const angle = (Math.PI * 2 * i) / count;
        const dist = spread * (0.3 + Math.random() * 0.7);
        pts.push([
          coord.lat + Math.sin(angle) * dist,
          coord.lng + Math.cos(angle) * dist / Math.cos((coord.lat * Math.PI) / 180),
          intensity * (0.4 + Math.random() * 0.5),
        ]);
      }
      return pts;
    });

    if (points.length === 0) return;

    const heat = L.heatLayer(points, {
      radius: 30,
      blur: 20,
      maxZoom: 11,
      max: 1.0,
      gradient: {
        0.15: "#166534",
        0.30: "#245c45",
        0.45: "#d97706",
        0.60: "#ea580c",
        0.75: "#ba1a1a",
        0.90: "#991b1b",
        1.0: "#7f1d1d",
      },
    });
    heat.addTo(map);
    layerRef.current = heat;
    return () => { if (layerRef.current) map.removeLayer(layerRef.current); };
  }, [risks, zones, map]);

  return null;
}

export default function RiskMap({ zones, risks, selectedId, reports, onSelect, intensification, hotspots, simulationResults, mapMode, onToggleMode }: {
  zones: Zone[]; risks: ZoneRisk[]; selectedId: string | null;
  reports: any[]; onSelect: (id: string) => void;
  intensification?: IntensificationResult[];
  hotspots?: Hotspot[];
  simulationResults?: SimulationResult[] | null;
  mapMode?: MapMode;
  onToggleMode?: (mode: MapMode) => void;
}) {
  const selectZone = useUIStore((s) => s.selectZone);
  const [roads, setRoads] = useState<RoadSegment[]>([]);

  useEffect(() => {
    getRoadSegments().then((r) => setRoads(r.roads)).catch(() => {});
  }, []);

  const intMap = useMemo(() => new Map(
    (intensification ?? []).map((i) => [i.zone_id, i])
  ), [intensification]);

  const topHotspots = useMemo(() =>
    (hotspots ?? []).filter((h) => h.priority === "CRITICAL" || h.priority === "HIGH").slice(0, 3),
    [hotspots]
  );

  if (mapMode === "3d") {
    return (
      <Terrain3DView
        zones={zones}
        risks={risks}
        roads={roads}
        selectedId={selectedId}
        onSelect={(id) => { selectZone(id); onSelect(id); }}
        onBackTo2D={() => onToggleMode?.("2d")}
      />
    );
  }

  return (
    <div className="relative h-full w-full">
      <MapContainer center={CENTER} zoom={8} className="h-full w-full"
                    preferCanvas style={{ background: "#e3e8e1" }}>
        <TileLayer
          attribution='Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics'
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" />

        <TileLayer
          url="https://tiles.wmflabs.org/hillshading/{z}/{x}/{y}.png"
          opacity={0.35}
          attribution='Hillshade SRTM' />

        <HeatmapLayer risks={risks} zones={zones} />

        <MapClickHandler zones={zones} />

        {simulationResults && <SimulationOverlay results={simulationResults} zones={zones} />}

        <CellHeatmapLayer zones={zones} />
        <TemporalCellAnimation visible={!!simulationResults} />

        {zones.map((z) => (
          <ZonePolygon key={z.id} zone={z} risk={risks.find((r) => r.zone_id === z.id)}
            selected={z.id === selectedId}
            onSelect={(id) => { selectZone(id); onSelect(id); }}
            intensification={intMap.get(z.id) ?? null} />
        ))}

        {topHotspots.map((h) => (
          <HotspotMarker key={h.zone_id} hotspot={h} zones={zones} />
        ))}

        {reports.filter((r) => r.status === "PENDING" || r.status === "VERIFIED")
                .map((r) => <ReportMarker key={r.id} report={r} />)}

        <MapLegend />
        <MapControls zones={zones} mapMode={mapMode} onToggleMode={onToggleMode} />
      </MapContainer>
    </div>
  )}

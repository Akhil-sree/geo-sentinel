import { MapContainer, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import ZonePolygon from "./ZonePolygon";
import {ReportMarker} from "./ReportMarker";
import MapLegend from "./MapLegend";
import MapControls from "./MapControls";
import { useUIStore } from "../../store/uiStore";
import type { Zone } from "../../types/zone";
import type { ZoneRisk } from "../../types/risk";

const CENTER: [number, number] = [25.45, 91.1]; // Meghalaya

export default function RiskMap({ zones, risks, selectedId, reports, onSelect }: {
  zones: Zone[]; risks: ZoneRisk[]; selectedId: string | null;
  reports: any[]; onSelect: (id: string) => void;
}) {
  const selectZone = useUIStore((s) => s.selectZone);

  return (
    <MapContainer center={CENTER} zoom={8} className="h-full w-full"
                  preferCanvas style={{ background: "#e3e8e1" }}>
      {/* base: realistic satellite imagery */}
      <TileLayer
        attribution='Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics'
        url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" />

      {/* overlay: hillshade for topographic relief */}
      <TileLayer
        url="https://tiles.wmflabs.org/hillshading/{z}/{x}/{y}.png"
        opacity={0.3}
        attribution='Hillshade SRTM' />

      {zones.map((z) => (
        <ZonePolygon key={z.id} zone={z} risk={risks.find((r) => r.zone_id === z.id)}
          selected={z.id === selectedId}
          onSelect={(id) => { selectZone(id); onSelect(id); }} />
      ))}

      {reports.filter((r) => r.status === "PENDING" || r.status === "VERIFIED")
              .map((r) => <ReportMarker key={r.id} report={r} />)}

      <MapLegend />
      <MapControls zones={zones} />

      {/* NOTE: escalation banner deliberately NOT here — it renders once,
          as a full-width strip in CommandCenter above the map. */}
    </MapContainer>
  )}

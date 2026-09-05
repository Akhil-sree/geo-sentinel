import { CircleMarker, Popup } from "react-leaflet";
import { useUIStore } from "../../store/uiStore";
import type { Hotspot } from "../../types/risk";
import type { Zone } from "../../types/zone";

const PRIORITY_COLORS: Record<string, string> = {
  CRITICAL: "#ba1a1a",
  HIGH: "#ea580c",
};

export default function HotspotMarker({ hotspot, zones }: { hotspot: Hotspot; zones: Zone[] }) {
  const selectZone = useUIStore((s) => s.selectZone);
  const zone = zones.find((z) => z.id === hotspot.zone_id);
  if (!zone) return null;

  const color = PRIORITY_COLORS[hotspot.priority] ?? "#d97706";

  return (
    <CircleMarker
      center={[zone.lat, zone.lng]}
      radius={12}
      pathOptions={{
        color,
        weight: 3,
        fillColor: color,
        fillOpacity: 0.2,
        className: "hotspot-pulse",
      }}
      eventHandlers={{ click: () => selectZone(hotspot.zone_id) }}
    >
      <Popup>
        <div className="min-w-[200px] text-xs">
          <div className="mb-1 flex items-center gap-2">
            <span className="flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold text-white"
              style={{ backgroundColor: color }}>
              {hotspot.rank}
            </span>
            <b>{hotspot.name}</b>
          </div>
          <div className="space-y-0.5 text-[11px]">
            <p><span className="font-semibold">Risk:</span> {(hotspot.risk_score * 100).toFixed(0)}%</p>
            <p><span className="font-semibold">Classification:</span> {hotspot.classification}</p>
            <p><span className="font-semibold">Trend:</span> {hotspot.trend}</p>
            {hotspot.sar_change_score != null && hotspot.sar_change_score > 0.3 && (
              <p className="font-bold text-amber-600">SAR change detected</p>
            )}
            {hotspot.escalated && (
              <p className="font-bold text-red-600">Escalation active</p>
            )}
          </div>
          <p className="mt-1 text-[9px] text-gray-500">Click polygon for full details</p>
        </div>
      </Popup>
    </CircleMarker>
  );
}

import { Polygon, Tooltip } from "react-leaflet";
import { SEV_COLOR, SEV_FILL_OPACITY } from "../../lib/severity";
import { fmtPctOpt } from "../../lib/format";
import { setPolygonClicked } from "../../lib/clickFlag";
import type { Zone } from "../../types/zone";
import type { ZoneRisk } from "../../types/risk";
import { zonePolygonCoords } from "../../lib/geo";

const STATE_OPACITY: Record<string, number> = {
  STABLE: 0.15,
  STRESSED: 0.18,
  DEGRADING: 0.28,
  CRITICAL: 0.38,
};

function severityLabel(sev: string): string {
  switch (sev) {
    case "VERY_HIGH": return "CRITICAL";
    case "HIGH": return "HIGH";
    case "MODERATE": return "MODERATE";
    default: return "LOW";
  }
}

interface ZonePolygonProps {
  zone: Zone;
  risk?: ZoneRisk;
  selected: boolean;
  onSelect: (id: string) => void;
  intensification?: { change: number; rate: string } | null;
  hotspotCount?: number;
  onZoneHover: (
    risk: ZoneRisk | null,
    position: { x: number; y: number } | null,
    hotspotCount: number,
  ) => void;
}

export default function ZonePolygon({
  zone,
  risk,
  selected,
  onSelect,
  intensification,
  hotspotCount = 0,
  onZoneHover,
}: ZonePolygonProps) {
  const sev = risk?.severity ?? "LOW";
  const slopeState = risk?.slope_state ?? null;

  const color = slopeState && risk?.slope_state_color
    ? risk.slope_state_color
    : SEV_COLOR[sev];

  const fillOpacity = slopeState
    ? STATE_OPACITY[slopeState] ?? SEV_FILL_OPACITY[sev] * 0.5
    : risk
      ? SEV_FILL_OPACITY[sev] * 0.4
      : 0.05;

  const borderWidth = selected ? 3
    : intensification
      ? intensification.change >= 0.10 ? 2
        : intensification.change >= 0.05 ? 1.5
        : 1
      : 1.2;

  return (
    <Polygon
      positions={zonePolygonCoords(zone)}
      pathOptions={{
        color: selected ? "#26332D" : color,
        weight: borderWidth,
        dashArray: sev === "MODERATE" && !slopeState ? "4" : undefined,
        fillColor: color,
        fillOpacity: selected ? Math.min(fillOpacity + 0.12, 0.5) : fillOpacity,
        className: risk?.escalated ? "gs-pulsing" : undefined,
      }}
      eventHandlers={{
        click: () => { setPolygonClicked(); onSelect(zone.id); },
        mouseover: (e) => {
          const container = e.target._map?.getContainer();
          if (container && risk) {
            const rect = container.getBoundingClientRect();
            const point = e.target._map.latLngToContainerPoint(e.latlng);
            onZoneHover(risk, { x: rect.left + point.x, y: rect.top + point.y }, hotspotCount);
          }
          if (e.target.setStyle) {
            e.target.setStyle({ weight: 3, fillOpacity: Math.min(fillOpacity + 0.08, 0.5) });
          }
        },
        mouseout: (e) => {
          onZoneHover(null, null, 0);
          if (e.target.setStyle) {
            e.target.setStyle({ weight: borderWidth, fillOpacity });
          }
        },
      }}
    >
      <Tooltip direction="top" opacity={1}>
        <div className="rounded-lg px-3 py-2 shadow-lg" style={{
          background: 'rgba(6, 18, 14, 0.85)',
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          border: '1px solid rgba(255, 255, 255, 0.10)',
          color: 'white',
        }}>
          <p className="text-[13px] font-bold">{zone.name}</p>
          {risk && (
            <p className="text-[11px]" style={{ color: 'rgba(255,255,255,0.6)' }}>
              {severityLabel(risk.severity)} RISK · {fmtPctOpt(risk.risk_score)}
            </p>
          )}
        </div>
      </Tooltip>
    </Polygon>
  );
}

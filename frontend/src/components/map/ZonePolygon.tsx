import { Polygon, Tooltip } from "react-leaflet";
import { SEV_COLOR, SEV_FILL_OPACITY } from "../../lib/severity";
import type { Zone } from "../../types/zone";
import type { ZoneRisk } from "../../types/risk";
import { zonePolygonCoords } from "../../lib/geo";

interface ZonePolygonProps {
  zone: Zone;
  risk?: ZoneRisk;
  selected: boolean;
  onSelect: (id: string) => void;
}

export default function ZonePolygon({
  zone,
  risk,
  selected,
  onSelect,
}: ZonePolygonProps) {
  const sev = risk?.severity ?? "LOW";
  const color = SEV_COLOR[sev];

  return (
    <Polygon
      positions={zonePolygonCoords(zone)}
      pathOptions={{
        color: selected ? "#1b1c17" : color,
        weight: selected ? 3 : 1,
        dashArray: sev === "MODERATE" ? "4" : undefined,
        fillColor: color,
        fillOpacity: risk
          ? sev === "VERY_HIGH"
            ? 0.55
            : SEV_FILL_OPACITY[sev]
          : 0.08,
        className: risk?.escalated ? "gs-pulsing" : undefined,
      }}
      eventHandlers={{
        click: () => onSelect(zone.id),
      }}
    >
      <Tooltip direction="top" opacity={1}>
        <b>{zone.name}</b>

        {" — "}

        {risk ? (
          <>
            <span>
              {risk.severity} ({risk.risk_score.toFixed(2)})
            </span>

            {risk.escalated && (
              <>
                <br />
                <span style={{ color: "#ba1a1a", fontWeight: 700 }}>
                  ▲ Escalation rule fired
                </span>
              </>
            )}
          </>
        ) : (
          "Loading risk data..."
        )}
      </Tooltip>
    </Polygon>
  );
}

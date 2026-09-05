import { Polygon, Tooltip, Popup } from "react-leaflet";
import { SEV_COLOR, SEV_FILL_OPACITY } from "../../lib/severity";
import { setPolygonClicked } from "../../lib/clickFlag";
import type { Zone } from "../../types/zone";
import type { ZoneRisk } from "../../types/risk";
import { zonePolygonCoords } from "../../lib/geo";

/** Slope-state fill opacity: smoother progression than severity-only */
const STATE_OPACITY: Record<string, number> = {
  STABLE: 0.15,
  STRESSED: 0.30,
  DEGRADING: 0.45,
  CRITICAL: 0.60,
};

interface ZonePolygonProps {
  zone: Zone;
  risk?: ZoneRisk;
  selected: boolean;
  onSelect: (id: string) => void;
  intensification?: { change: number; rate: string } | null;
}

export default function ZonePolygon({
  zone,
  risk,
  selected,
  onSelect,
  intensification,
}: ZonePolygonProps) {
  const sev = risk?.severity ?? "LOW";
  const slopeState = risk?.slope_state ?? null;

  // Prefer slope state color when available, fall back to severity
  const color = slopeState && risk?.slope_state_color
    ? risk.slope_state_color
    : SEV_COLOR[sev];

  const fillOpacity = slopeState
    ? STATE_OPACITY[slopeState] ?? SEV_FILL_OPACITY[sev]
    : risk
      ? SEV_FILL_OPACITY[sev]
      : 0.08;

  // Intensification indicator: thicken border when risk is increasing
  const borderWidth = intensification
    ? intensification.change >= 0.10 ? 3
      : intensification.change >= 0.05 ? 2
      : 1
    : selected ? 3 : 1;

  return (
    <Polygon
      positions={zonePolygonCoords(zone)}
      pathOptions={{
        color: selected ? "#1b1c17" : color,
        weight: borderWidth,
        dashArray: sev === "MODERATE" && !slopeState ? "4" : undefined,
        fillColor: color,
        fillOpacity,
        className: risk?.escalated ? "gs-pulsing" : undefined,
      }}
      eventHandlers={{
        click: () => { setPolygonClicked(); onSelect(zone.id); },
      }}
    >
      <Tooltip direction="top" opacity={1}>
        <b>{zone.name}</b>

        {" — "}

        {risk ? (
          <>
            {slopeState && (
              <span style={{ color: risk.slope_state_color ?? color, fontWeight: 700 }}>
                {risk.slope_state_label ?? slopeState}
              </span>
            )}
            {" "}
            <span>
              {risk.severity} ({risk.risk_score.toFixed(2)})
            </span>

            {risk.escalated && (
              <>
                <br />
                <span style={{ color: "#ba1a1a", fontWeight: 700 }}>
                  Escalation rule active
                </span>
              </>
            )}

            {intensification && intensification.change >= 0.05 && (
              <>
                <br />
                <span style={{ color: intensification.change >= 0.15 ? "#ba1a1a" : "#d97706", fontWeight: 700 }}>
                  Risk {intensification.change >= 0 ? "increasing" : "decreasing"}
                  {" "}({intensification.change >= 0 ? "+" : ""}
                  {(intensification.change * 100).toFixed(1)}%)
                </span>
              </>
            )}
          </>
        ) : (
          "Loading risk data..."
        )}
      </Tooltip>
      {selected && (
        <Popup maxWidth={280}>
          <div className="min-w-[220px] text-xs">
            <div className="mb-1 flex items-center justify-between">
              <b className="text-sm">{zone.name}</b>
              {risk?.slope_state && (
                <span className="rounded px-1.5 py-0.5 text-[9px] font-bold text-white"
                  style={{ backgroundColor: risk.slope_state_color }}>
                  {risk.slope_state_label ?? risk.slope_state}
                </span>
              )}
            </div>
            {risk && (
              <div className="mt-1.5 space-y-1">
                <div className="grid grid-cols-2 gap-1">
                  <div className="rounded bg-gray-50 p-1">
                    <p className="text-[8px] text-gray-500">RISK SCORE</p>
                    <p className="text-sm font-bold" style={{ color: risk.slope_state_color }}>
                      {(risk.risk_score * 100).toFixed(0)}%
                    </p>
                  </div>
                  <div className="rounded bg-gray-50 p-1">
                    <p className="text-[8px] text-gray-500">SEVERITY</p>
                    <p className="text-sm font-bold text-gray-800">{risk.severity}</p>
                  </div>
                </div>
                {risk.slope_stress_score != null && (
                  <div>
                    <div className="flex justify-between text-[8px] text-gray-500">
                      <span>Slope Stress</span>
                      <span>{(risk.slope_stress_score * 100).toFixed(0)}%</span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-gray-200">
                      <div className="h-1.5 rounded-full" style={{
                        width: `${risk.slope_stress_score * 100}%`,
                        backgroundColor: risk.slope_state_color,
                      }} />
                    </div>
                  </div>
                )}
                {risk.escalated && (
                  <p className="rounded bg-red-50 px-1 py-0.5 text-[9px] font-bold text-red-600">
                    ESCALATION RULE ACTIVE
                  </p>
                )}
                {intensification && Math.abs(intensification.change) >= 0.05 && (
                  <p className="text-[9px] font-semibold" style={{ color: intensification.change >= 0 ? "#ba1a1a" : "#245c45" }}>
                    {intensification.change >= 0 ? "↑" : "↓"} Risk {intensification.change >= 0 ? "increasing" : "decreasing"}
                    {" "}({intensification.change >= 0 ? "+" : ""}{(intensification.change * 100).toFixed(1)}%)
                  </p>
                )}
                <p className="text-[9px] text-gray-500 mt-1">View full analysis in sidebar →</p>
              </div>
            )}
          </div>
        </Popup>
      )}
    </Polygon>
  );
}

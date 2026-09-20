import { CircleMarker, Popup } from "react-leaflet";
import { useUIStore } from "../../store/uiStore";
import { fmtPctOpt } from "../../lib/format";
import type { SimulationResult } from "../../types/risk";
import type { Zone } from "../../types/zone";

const num = (v: number | null | undefined) =>
  typeof v === "number" && Number.isFinite(v) ? v : null;

export default function SimulationOverlay({ results, zones }: { results: SimulationResult[]; zones: Zone[] }) {
  const selectZone = useUIStore((s) => s.selectZone);

  return (
    <>
      {results.filter((r) => num(r.simulated_risk) !== null && num(r.current_risk) !== null && Math.abs((r.simulated_risk as number) - (r.current_risk as number)) > 0.05).map((r) => {
        const zone = zones.find((z) => z.id === r.zone_id);
        if (!zone) return null;
        const delta = (r.simulated_risk as number) - (r.current_risk as number);
        const color = delta > 0.15 ? "#ba1a1a" : delta > 0.05 ? "#ea580c" : "#d97706";

        return (
          <CircleMarker
            key={`sim-${r.zone_id}`}
            center={[zone.lat, zone.lng]}
            radius={18}
            pathOptions={{
              color,
              weight: 2,
              fillColor: color,
              fillOpacity: 0.15,
              dashArray: "6 4",
              className: "sim-flash",
            }}
            eventHandlers={{ click: () => selectZone(r.zone_id) }}
          >
            <Popup>
              <div className="min-w-[180px] text-xs">
                <b className="text-sm">{r.name}</b>
                <div className="mt-1 space-y-0.5">
                  <p><span className="font-semibold">Current:</span> {fmtPctOpt(num(r.current_risk))}</p>
                  <p><span className="font-semibold">Simulated:</span> <span style={{ color: r.slope_state_color }}>{fmtPctOpt(num(r.simulated_risk))}</span></p>
                  <p><span className="font-semibold">Change:</span> <span style={{ color }}>{delta > 0 ? "+" : ""}{(delta * 100).toFixed(1)}%</span></p>
                  <p><span className="font-semibold">State:</span> {r.slope_state_label}</p>
                  {r.escalated && <p className="font-bold text-red-600">ESCALATION TRIGGERED</p>}
                </div>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </>
  );
}

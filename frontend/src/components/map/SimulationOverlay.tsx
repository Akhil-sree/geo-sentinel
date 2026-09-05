import { CircleMarker, Popup } from "react-leaflet";
import { useUIStore } from "../../store/uiStore";
import type { SimulationResult } from "../../types/risk";
import type { Zone } from "../../types/zone";

export default function SimulationOverlay({ results, zones }: { results: SimulationResult[]; zones: Zone[] }) {
  const selectZone = useUIStore((s) => s.selectZone);

  return (
    <>
      {results.filter((r) => Math.abs(r.simulated_risk - r.current_risk) > 0.05).map((r) => {
        const zone = zones.find((z) => z.id === r.zone_id);
        if (!zone) return null;
        const delta = r.simulated_risk - r.current_risk;
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
                  <p><span className="font-semibold">Current:</span> {(r.current_risk * 100).toFixed(0)}%</p>
                  <p><span className="font-semibold">Simulated:</span> <span style={{ color: r.slope_state_color }}>{(r.simulated_risk * 100).toFixed(0)}%</span></p>
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

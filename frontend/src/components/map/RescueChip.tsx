import { useUIStore } from "../../store/uiStore";

/** Compact floating rescue card (§17). Same store object as panel + layer. */
export default function RescueChip() {
  const route = useUIStore((s) => s.rescueRoute);
  const status = useUIStore((s) => s.rescueStatus);
  const journeyPhase = useUIStore((s) => s.journeyPhase);
  const setJourneyPhase = useUIStore((s) => s.setJourneyPhase);
  const resetJourney = useUIStore((s) => s.resetJourney);
  const clearRescueRoute = useUIStore((s) => s.clearRescueRoute);

  if (status !== "success" || !route?.route_available) return null;

  return (
    <div
      className="rescue-chip absolute z-[500] rounded-lg p-3"
      style={{
        left: 12,
        bottom: 12,
        width: 230,
        background: "rgba(255,255,255,0.97)",
        border: "1px solid #E5E7EB",
        boxShadow: "0 2px 10px rgba(0,0,0,0.15)",
      }}
    >
      <div className="text-[10px] font-bold uppercase tracking-wider text-gs-text-secondary">
        Rescue route
      </div>
      <div className="text-[12px] font-bold text-gs-text truncate">
        {(route.originName ?? "Origin")} → {(route.destName ?? "Destination")}
      </div>
      <div className="mt-1 flex items-baseline gap-2 text-[12px]">
        <span className="font-bold tabular-nums text-gs-text">{route.distance_km} km</span>
        <span className="tabular-nums text-gs-text-secondary">~{route.eta_min ?? "—"} min</span>
        <span className="text-[10px] uppercase tracking-wide text-gs-text-secondary">lower-exposure</span>
      </div>
      <div className="text-[10px] text-gs-text-secondary">
        {route.blocked_avoided?.length ?? 0} blocked avoided
      </div>
      <div className="mt-2 flex gap-1.5">
        {journeyPhase === "running" ? (
          <button
            onClick={() => setJourneyPhase("paused")}
            className="flex-1 rounded-md bg-forest py-1 text-[11px] font-semibold text-white"
          >
            ❚❚
          </button>
        ) : (
          <button
            onClick={() => {
              if (journeyPhase !== "paused") resetJourney();
              setJourneyPhase("running");
            }}
            className="flex-1 rounded-md bg-risk-stable py-1 text-[11px] font-semibold text-white"
          >
            {journeyPhase === "paused" ? "▶" : journeyPhase === "done" ? "↻" : "▶ GO"}
          </button>
        )}
        <button
          onClick={() => clearRescueRoute()}
          className="rounded-md px-2 py-1 text-[11px] font-semibold text-gs-text"
          style={{ border: "1px solid #E5E7EB" }}
        >
          ✕
        </button>
      </div>
    </div>
  );
}

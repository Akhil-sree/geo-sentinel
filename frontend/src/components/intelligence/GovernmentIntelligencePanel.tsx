import { useEffect, useState } from "react";
import { getHotspotRanking, getRiskIntensification } from "../../api/risk";
import { useUIStore } from "../../store/uiStore";
import type { Hotspot, IntensificationResult } from "../../types/risk";

const INTERP_ICONS: Record<string, string> = {
  RAPIDLY_INTENSIFYING: "\u2191\u2191",
  GRADUALLY_INCREASING: "\u2191",
  STABLE: "\u2192",
  DECREASING: "\u2193",
  VARIABLE: "\u2194",
  NO_DATA: "-",
};

export default function GovernmentIntelligencePanel() {
  const [hotspots, setHotspots] = useState<Hotspot[]>([]);
  const [intensification, setIntensification] = useState<IntensificationResult[]>([]);
  const [loading, setLoading] = useState(true);
  const simTime = useUIStore((s) => s.simTime);
  const selectZone = useUIStore((s) => s.selectZone);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getHotspotRanking(simTime),
      getRiskIntensification(simTime),
    ])
      .then(([h, i]) => {
        setHotspots(h.hotspots);
        setIntensification(i.intensification);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [simTime]);

  const top3 = hotspots.slice(0, 3);
  const rising = intensification.filter((z) => z.change >= 0.05).slice(0, 3);

  if (loading) {
    return (
      <div className="rounded bg-white p-3 shadow-sm">
        <p className="text-[10px] font-bold text-[#707973]">LOADING INTELLIGENCE...</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">

      {/* Emerging hotspots summary */}
      <div className="rounded bg-white p-3 shadow-sm">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-[10px] font-bold uppercase tracking-wide text-[#1b1c17]">
            Early Warning Intelligence
          </h3>
          <span className="rounded bg-[#ba1a1a]/10 px-1.5 py-0.5 text-[8px] font-bold text-[#ba1a1a]">
            {top3.filter((h) => h.priority === "CRITICAL").length} CRITICAL
          </span>
        </div>

        {top3.length === 0 ? (
          <p className="text-[9px] text-[#707973]">No significant hotspots.</p>
        ) : (
          <div className="space-y-1.5">
            {top3.map((h) => (
              <button
                key={h.zone_id}
                onClick={() => selectZone(h.zone_id)}
                className="w-full rounded border border-[#e4e3db] p-2 text-left transition-colors hover:border-[#04442f]/30 hover:bg-[#f0eee6]"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className={`flex h-4 w-4 items-center justify-center rounded-full text-[8px] font-bold text-white ${
                      h.priority === "CRITICAL" ? "bg-[#ba1a1a]" : "bg-[#d97706]"
                    }`}>
                      {h.rank}
                    </span>
                    <span className="text-[10px] font-bold text-[#1b1c17]">{h.name}</span>
                  </div>
                  <span className="text-[10px] font-bold text-[#04442f]">
                    {(h.risk_score * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="mt-1 flex items-center gap-1.5 text-[8px]">
                  <span style={{ color: h.trajectory_interpretation.includes("INTENSIFYING") ? "#ba1a1a" : "#707973" }}>
                    {INTERP_ICONS[h.trajectory_interpretation] ?? ""} {h.trajectory_interpretation.replace(/_/g, " ")}
                  </span>
                  {h.escalated && (
                    <span className="rounded bg-[#ba1a1a]/10 px-1 py-0.5 text-[7px] font-bold text-[#ba1a1a]">
                      ESC
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Risk intensification */}
      {rising.length > 0 && (
        <div className="rounded bg-white p-3 shadow-sm">
          <h3 className="mb-1.5 text-[10px] font-bold uppercase tracking-wide text-[#1b1c17]">
            Risk Intensification
          </h3>
          <div className="space-y-1">
            {rising.map((z) => (
              <button
                key={z.zone_id}
                onClick={() => selectZone(z.zone_id)}
                className="flex w-full items-center justify-between rounded border border-[#e4e3db] p-1.5 text-left hover:border-[#04442f]/30"
              >
                <span className="text-[9px] font-bold text-[#1b1c17]">{z.name}</span>
                <div className="flex items-center gap-1.5">
                  <span className="text-[8px] text-[#707973]">
                    {z.change >= 0 ? "+" : ""}{(z.change * 100).toFixed(1)}%
                  </span>
                  <span
                    className="rounded px-1 py-0.5 text-[7px] font-bold text-white"
                    style={{ backgroundColor: z.color }}
                  >
                    {z.rate}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

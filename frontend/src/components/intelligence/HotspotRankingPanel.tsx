import { useEffect, useState } from "react";
import { getHotspotRanking } from "../../api/risk";
import { useUIStore } from "../../store/uiStore";
import type { Hotspot } from "../../types/risk";

const TREND_ICONS: Record<string, string> = {
  Rapid: "\u2191",
  Moderate: "\u2191",
  Stable: "\u2192",
  None: "\u2192",
};

const CLASSIFICATION_LABELS: Record<string, string> = {
  EMERGING: "Emerging Hotspot",
  INTENSIFYING: "Intensifying",
  PERSISTENT: "Persistent High",
  LOW_CONCERN: "Low Concern",
  STABLE: "Stable",
};

const CLASSIFICATION_COLORS: Record<string, string> = {
  EMERGING: "#ba1a1a",
  INTENSIFYING: "#ea580c",
  PERSISTENT: "#d97706",
  LOW_CONCERN: "#245c45",
  STABLE: "#707973",
};

export default function HotspotRankingPanel() {
  const [hotspots, setHotspots] = useState<Hotspot[]>([]);
  const [loading, setLoading] = useState(true);
  const simTime = useUIStore((s) => s.simTime);
  const selectZone = useUIStore((s) => s.selectZone);

  useEffect(() => {
    setLoading(true);
    getHotspotRanking(simTime)
      .then((r) => setHotspots(r.hotspots))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [simTime]);

  const top3 = hotspots.filter((h) => h.priority === "CRITICAL" || h.priority === "HIGH").slice(0, 3);

  if (loading) {
    return (
      <div className="rounded bg-white p-3 shadow-sm">
        <p className="text-[10px] font-bold text-[#707973]">ANALYZING HOTSPOTS...</p>
      </div>
    );
  }

  return (
    <div className="rounded bg-white p-3 shadow-sm">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-[10px] font-bold uppercase tracking-wide text-[#1b1c17]">
          Spatiotemporal Hotspot Ranking
        </h3>
        <span className="rounded bg-[#04442f]/10 px-1.5 py-0.5 text-[8px] font-bold text-[#04442f]">
          EHSA-INSPIRED
        </span>
      </div>

      {top3.length === 0 ? (
        <p className="text-[9px] text-[#707973]">No significant hotspots detected.</p>
      ) : (
        <div className="space-y-2">
          {top3.map((h) => (
            <button
              key={h.zone_id}
              onClick={() => selectZone(h.zone_id)}
              className="w-full rounded border border-[#e4e3db] p-2 text-left transition-colors hover:border-[#04442f]/30 hover:bg-[#f0eee6]"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#04442f] text-[9px] font-bold text-white">
                    {h.rank}
                  </span>
                  <div>
                    <p className="text-[10px] font-bold text-[#1b1c17]">{h.name}</p>
                    <p className="text-[8px] text-[#707973]">{h.district}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-[10px] font-bold text-[#04442f]">
                    {(h.risk_score * 100).toFixed(0)}%
                  </p>
                  <p className="text-[8px] font-bold" style={{ color: CLASSIFICATION_COLORS[h.classification] }}>
                    {TREND_ICONS[h.trend] ?? ""} {h.trend}
                  </p>
                </div>
              </div>

              <div className="mt-1.5 flex items-center gap-2">
                <span
                  className="rounded px-1 py-0.5 text-[7px] font-bold"
                  style={{
                    color: CLASSIFICATION_COLORS[h.classification],
                    backgroundColor: `${CLASSIFICATION_COLORS[h.classification]}15`,
                  }}
                >
                  {CLASSIFICATION_LABELS[h.classification]}
                </span>
                {h.escalated && (
                  <span className="rounded bg-[#ba1a1a]/10 px-1 py-0.5 text-[7px] font-bold text-[#ba1a1a]">
                    ESCALATED
                  </span>
                )}
                {h.sar_change_score && h.sar_change_score > 0.3 && (
                  <span className="rounded bg-[#d97706]/10 px-1 py-0.5 text-[7px] font-bold text-[#d97706]">
                    SAR
                  </span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}

      {hotspots.length > 3 && (
        <p className="mt-2 text-[8px] text-[#707973]">
          +{hotspots.length - 3} additional zones monitored
        </p>
      )}
    </div>
  );
}

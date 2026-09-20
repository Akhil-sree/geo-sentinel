import { useEffect, useState, useMemo } from "react";
import { getHotspotRanking, getRiskIntensification } from "../../api/risk";
import { useUIStore } from "../../store/uiStore";
import { fmtPctOpt, fmtMmOpt } from "../../lib/format";
import type { Hotspot, IntensificationResult } from "../../types/risk";

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: "#B91C1C",
  HIGH: "#E55A2B",
  MODERATE: "#F2A623",
  LOW: "#2563EB",
};

const TREND_LABELS: Record<string, { text: string; color: string; icon: string }> = {
  RAPIDLY_INTENSIFYING: { text: "Risk increasing", color: "#B91C1C", icon: "↑" },
  GRADUALLY_INCREASING: { text: "Risk increasing", color: "#E55A2B", icon: "↑" },
  STABLE: { text: "Stable", color: "#2563EB", icon: "→" },
  DECREASING: { text: "Decreasing", color: "#2563EB", icon: "↓" },
  VARIABLE: { text: "Variable trend", color: "#F2A623", icon: "↔" },
  NO_DATA: { text: "Insufficient data", color: "#65736C", icon: "–" },
};

const CLASSIFICATION_LABELS: Record<string, string> = {
  EMERGING: "Event-triggered",
  INTENSIFYING: "Event-triggered",
  PERSISTENT: "Persistent",
  LOW_CONCERN: "Shallow",
  STABLE: "Shallow",
};

function soilLabel(sm: number | null | undefined): string {
  if (typeof sm !== "number" || !Number.isFinite(sm)) return "—";
  if (sm > 0.45) return "Saturated";
  if (sm > 0.3) return "Elevated";
  return "Normal";
}

function soilColor(sm: number | null | undefined): string {
  if (typeof sm !== "number" || !Number.isFinite(sm)) return "#65736C";
  if (sm > 0.45) return "#B91C1C";
  if (sm > 0.3) return "#F2A623";
  return "#2563EB";
}

export default function GovernmentIntelligencePanel() {
  const [hotspots, setHotspots] = useState<Hotspot[]>([]);
  const [intensification, setIntensification] = useState<IntensificationResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState<"risk" | "trend">("risk");
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

  const sortedHotspots = useMemo(() => {
    const list = [...hotspots];
    if (sortBy === "risk")
      list.sort(
        (a, b) => (b.risk_score ?? -1) - (a.risk_score ?? -1),
      );
    return list;
  }, [hotspots, sortBy]);

  const escalatingCount = hotspots.filter(
    (h) => h.trajectory_interpretation?.includes("INTENSIFYING") || h.trajectory_interpretation?.includes("INCREASING")
  ).length;

  const now = new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Kolkata" });

  if (loading) {
    return (
      <div className="rounded-lg p-5" style={{
        background: '#FFFFFF',
        border: '1px solid #E5E7EB',
      }}>
        <p className="text-[15px] font-medium text-gs-text-secondary">Loading intelligence…</p>
      </div>
    );
  }

  if (sortedHotspots.length === 0) {
    return (
      <div className="space-y-4">
        <div className="mb-2 flex items-center gap-3">
          <h2 className="text-[22px] font-bold text-gs-text tracking-tight">
            EARLY WARNING INTELLIGENCE
          </h2>
        </div>
        <div className="rounded-lg p-8 flex flex-col items-center justify-center text-center" style={{
          background: '#FFFFFF',
          border: '1px solid #E5E7EB',
        }}>
          <svg className="mb-3 h-10 w-10 text-risk-low" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-[16px] font-semibold text-gs-text">All zones within safe parameters</p>
          <p className="mt-1 text-[13px] text-gs-text-secondary">No areas currently require elevated attention</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">

      {/* Header */}
      <div className="mb-2 flex items-start justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-[22px] font-bold text-gs-text tracking-tight">
            EARLY WARNING INTELLIGENCE
          </h2>
          {escalatingCount > 0 && (
            <span className="shrink-0 inline-flex items-center rounded-full bg-risk-critical/10 px-2.5 py-1 text-[12px] font-bold text-risk-critical ring-1 ring-risk-critical/20">
              {escalatingCount} zones escalating
            </span>
          )}
        </div>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as "risk" | "trend")}
          className="shrink-0 rounded-md px-2.5 py-1.5 text-[13px] font-medium text-gs-text-secondary focus:outline-none focus:ring-1 focus:ring-forest/30"
          style={{
            background: '#EDE8D9',
            border: '1px solid #D6D3CA',
          }}
        >
          <option value="risk">Sort by: Risk ▾</option>
          <option value="trend">Sort by: Trend ▾</option>
        </select>
      </div>

      {/* Zone Intelligence Cards */}
      <div className="space-y-4">
        {sortedHotspots.map((h, idx) => {
          const sevColor = SEVERITY_COLORS[h.priority] ?? SEVERITY_COLORS.LOW;
          const trend = TREND_LABELS[h.trajectory_interpretation] ?? TREND_LABELS.NO_DATA;
          const soilVal = soilLabel(h.soil_moisture);
          const soilC = soilColor(h.soil_moisture);
          const classLabel = CLASSIFICATION_LABELS[h.classification] ?? h.classification?.replace(/_/g, " ") ?? "—";

          return (
            <div key={h.zone_id}>
              <button
                onClick={() => selectZone(h.zone_id)}
                className="w-full rounded-card text-left transition-all overflow-hidden"
                style={{
                  background: '#FFFFFF',
                  border: '1px solid #E5E7EB',
                  borderLeftWidth: 4, borderLeftColor: sevColor,
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = '#F9FAFB'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = '#FFFFFF'; }}
              >
                <div className="p-4">
                  {/* Header Row: Badge + Name + Risk % */}
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-start gap-2.5">
                      <div
                        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[14px] font-bold text-white"
                        style={{ backgroundColor: sevColor }}
                      >
                        {idx + 1}
                      </div>
                      <div>
                        <h3 className="text-[16px] font-semibold text-gs-text leading-tight">
                          {h.name}
                        </h3>
                        <p className="text-[12px] text-gs-text-secondary mt-0.5">
                          {h.district} · Meghalaya
                        </p>
                      </div>
                    </div>
                    <span className="text-[24px] font-bold" style={{ color: sevColor }}>
                      {fmtPctOpt(h.risk_score)}
                    </span>
                  </div>

                  {/* Trend (backend-provided trajectory only — no synthetic history) */}
                  <div className="flex items-center gap-2 mb-2.5">
                    <span className="text-[11px] text-gs-text-secondary">
                      Model risk score (uncalibrated — not a probability)
                    </span>
                  </div>

                  {/* Status Badges */}
                  <div className="flex items-center gap-2 mb-3">
                    <span className="inline-flex items-center gap-1 text-[13px] font-medium" style={{ color: trend.color }}>
                      {trend.icon} {trend.text}
                    </span>
                    {h.escalated && (
                      <span className="inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-bold text-white" style={{ backgroundColor: "#B91C1C" }}>
                        ESCALATED
                      </span>
                    )}
                    {!h.escalated && h.priority === "CRITICAL" && (
                      <span className="inline-flex items-center rounded-md bg-risk-critical/10 px-2 py-0.5 text-[11px] font-semibold text-risk-critical ring-1 ring-risk-critical/20">
                        WATCH
                      </span>
                    )}
                    {!h.escalated && h.priority !== "CRITICAL" && (
                      <span className="inline-flex items-center rounded-md bg-risk-low/10 px-2 py-0.5 text-[11px] font-semibold text-risk-low ring-1 ring-risk-low/20">
                        STABLE
                      </span>
                    )}
                  </div>

                  {/* Metrics Row */}
                  <div className="grid grid-cols-3 gap-2 pt-2.5 border-t border-gs-border/60">
                    <div>
                      <p className="text-[11px] text-gs-text-secondary mb-0.5">Rainfall</p>
                      <p className="text-[15px] font-semibold text-gs-text">{fmtMmOpt(h.rainfall_72h)}</p>
                    </div>
                    <div>
                      <p className="text-[11px] text-gs-text-secondary mb-0.5">Soil moisture</p>
                      <p className="text-[15px] font-semibold" style={{ color: soilC }}>
                        {soilVal}
                      </p>
                    </div>
                    <div>
                      <p className="text-[11px] text-gs-text-secondary mb-0.5">Classification</p>
                      <p className="text-[15px] font-semibold text-gs-text capitalize">
                        {classLabel}
                      </p>
                    </div>
                  </div>

                  {/* Temporal prediction: explicitly unavailable (no validated forecast) */}
                  <div className="mt-3 -mx-4 -mb-4 px-4 py-2.5 bg-forest/[0.04] border-t border-gs-border/40">
                    <p className="text-[12px] text-gs-text-secondary italic">
                      Temporal prediction: unavailable
                    </p>
                  </div>
                </div>
              </button>

              {/* Divider with timestamp */}
              {idx < sortedHotspots.length - 1 && (
                <div className="flex items-center gap-3 my-1 px-2">
                  <span className="h-px flex-1 bg-gs-border/60" />
                  <span className="text-[10px] text-gs-text-secondary/60 font-mono whitespace-nowrap">
                    Updated {now}
                  </span>
                  <span className="h-px flex-1 bg-gs-border/60" />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Risk Intensification */}
      {intensification.filter((z) => z.change >= 0.05).length > 0 && (
        <div className="mt-4">
          <h3 className="text-[16px] font-semibold text-gs-text mb-3">
            RISK INTENSIFICATION
          </h3>
          <div className="space-y-2">
            {intensification.filter((z) => z.change >= 0.05).slice(0, 3).map((z) => (
              <button
                key={z.zone_id}
                onClick={() => selectZone(z.zone_id)}
                className="flex w-full items-center justify-between rounded-card p-3 text-left transition-all"
                style={{
                  background: '#FFFFFF',
                  border: '1px solid #E5E7EB',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = '#F9FAFB'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = '#FFFFFF'; }}
              >
                <div className="flex items-center gap-3">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-risk-high/10 text-[13px] font-bold text-risk-high">
                    ↑
                  </span>
                  <div>
                    <span className="text-[14px] font-semibold text-gs-text block">{z.name}</span>
                    <span className="text-[12px] text-gs-text-secondary">
                      {z.change >= 0 ? "+" : ""}{(z.change * 100).toFixed(1)}% change
                    </span>
                  </div>
                </div>
                <span
                  className="rounded-md px-2.5 py-1 text-[12px] font-semibold text-white"
                  style={{ backgroundColor: z.color }}
                >
                  {z.rate}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

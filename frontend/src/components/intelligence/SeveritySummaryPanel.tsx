import { useEffect, useState } from "react";
import { getSeveritySummary } from "../../api/dashboard";
import { useUIStore } from "../../store/uiStore";
import { fmtPctOpt } from "../../lib/format";
import Spinner from "../common/Spinner";
import type { SeveritySummary as SeveritySummaryType } from "../../types/risk";

const SEVERITY_COLORS: Record<string, string> = {
  LOW: "#2563EB",
  MODERATE: "#d97706",
  HIGH: "#ea580c",
  VERY_HIGH: "#ba1a1a",
};

export default function SeveritySummaryPanel() {
  const simTime = useUIStore((s) => s.simTime);
  const [summary, setSummary] = useState<SeveritySummaryType | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getSeveritySummary(simTime)
      .then(setSummary)
      .catch(() => setSummary(null))
      .finally(() => setLoading(false));
  }, [simTime]);

  if (loading) {
    return (
      <div className="rounded-card p-4" style={{ background: 'rgba(229, 233, 224, 0.45)', backdropFilter: 'blur(8px)', border: '1px solid rgba(255,255,255,0.18)' }}>
        <div className="flex items-center gap-2 text-[14px] text-gs-text-secondary"><Spinner /> Loading summary...</div>
      </div>
    );
  }

  if (!summary) return null;

  const total = summary.total_zones;
  const maxCount = Math.max(...Object.values(summary.summary), 1);

  return (
    <div className="rounded-card p-4" style={{ background: 'rgba(229, 233, 224, 0.45)', backdropFilter: 'blur(8px)', border: '1px solid rgba(255,255,255,0.18)' }}>
      <h3 className="text-[15px] font-bold text-gs-text mb-1">Severity Summary</h3>
      <p className="text-[12px] text-gs-text-secondary mb-3">{total} zones · Pop. {summary.total_population.toLocaleString()}</p>

      {/* Key stats */}
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div className="rounded-lg p-2 text-center" style={{ background: 'rgba(255,255,255,0.4)' }}>
          <div className="text-[18px] font-bold text-gs-text">{summary.exposed_population.toLocaleString()}</div>
          <div className="text-[11px] text-gs-text-secondary">Exposed Population</div>
        </div>
        <div className="rounded-lg p-2 text-center" style={{ background: 'rgba(255,255,255,0.4)' }}>
          <div className="text-[18px] font-bold text-red-700">{summary.escalated_count}</div>
          <div className="text-[11px] text-gs-text-secondary">Escalated Zones</div>
        </div>
      </div>

      {/* Severity distribution */}
      <div className="space-y-2 mb-3">
        {(["VERY_HIGH", "HIGH", "MODERATE", "LOW"] as const).map((sev) => {
          const count = summary.summary[sev] || 0;
          const pct = (count / maxCount) * 100;
          return (
            <div key={sev} className="flex items-center gap-2">
              <span className="w-16 text-[11px] text-gs-text-secondary">{sev.replace("_", " ")}</span>
              <div className="flex-1 h-3 rounded-full bg-white/40 overflow-hidden">
                <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: SEVERITY_COLORS[sev] }} />
              </div>
              <span className="w-6 text-right text-[12px] font-bold" style={{ color: SEVERITY_COLORS[sev] }}>{count}</span>
            </div>
          );
        })}
      </div>

      {/* Zone breakdown */}
      <div className="text-[12px] font-semibold text-gs-text mb-1">Zone Risk Breakdown</div>
      <div className="space-y-1 max-h-48 overflow-y-auto">
        {summary.zones.map((z) => (
          <div key={z.zone_id} className="flex items-center justify-between rounded-md px-2 py-1.5" style={{ background: 'rgba(255,255,255,0.3)' }}>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full" style={{ background: SEVERITY_COLORS[z.severity] }} />
              <span className="text-[12px] text-gs-text">{z.name}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-medium text-gs-text">{fmtPctOpt(z.risk_score)}</span>
              {z.escalated && <span className="text-[9px] text-red-700 font-bold">ESC</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

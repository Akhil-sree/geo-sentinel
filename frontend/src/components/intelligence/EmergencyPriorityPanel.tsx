import { useEffect, useState } from "react";
import { getEmergencyPriorities } from "../../api/risk";
import { useUIStore } from "../../store/uiStore";
import type { EmergencyPriority } from "../../api/risk";
import { t } from "../../lib/i18n";

export default function EmergencyPriorityPanel() {
  const [priorities, setPriorities] = useState<EmergencyPriority[]>([]);
  const [loading, setLoading] = useState(false);
  const simTime = useUIStore((s) => s.simTime);
  const selectZone = useUIStore((s) => s.selectZone);

  useEffect(() => {
    setLoading(true);
    getEmergencyPriorities(simTime)
      .then((r) => setPriorities(r.priorities))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [simTime]);

  if (loading) {
    return (
      <div className="rounded-lg border border-[#d9e2d9] bg-white p-3 shadow-sm">
        <div className="flex items-center gap-2">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-[#ba1a1a] border-t-transparent" />
          <span className="text-[10px] text-[#707973]">Computing priorities...</span>
        </div>
      </div>
    );
  }

  if (priorities.length === 0) return null;

  const criticalCount = priorities.filter((p) => p.tier === "CRITICAL").length;
  const highCount = priorities.filter((p) => p.tier === "HIGH").length;

  return (
    <div className="overflow-hidden rounded-lg border border-[#ba1a1a]/20 bg-white shadow-sm">
      {/* Header */}
      <div className="border-b border-[#e4e3db] bg-gradient-to-r from-[#ba1a1a] to-[#991b1b] px-3 py-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-white/20 text-white">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M7 1L1 13h12L7 1z" stroke="white" strokeWidth="1.5" fill="none"/>
                <path d="M7 5v4M7 10.5v0" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </span>
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wide text-white">
                {t("emergencyPriority")}
              </p>
              <p className="text-[8px] text-white/70">
                Composite urgency: risk + population + accessibility
              </p>
            </div>
          </div>
          <div className="text-right">
            {criticalCount > 0 && (
              <span className="rounded bg-white/20 px-1.5 py-0.5 text-[8px] font-bold text-white">
                {criticalCount} CRITICAL
              </span>
            )}
            {highCount > 0 && (
              <span className="ml-1 rounded bg-white/20 px-1.5 py-0.5 text-[8px] font-bold text-white">
                {highCount} HIGH
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Priority list */}
      <div className="divide-y divide-[#e4e3db]">
        {priorities.map((p) => (
          <button
            key={p.zone_id}
            onClick={() => selectZone(p.zone_id)}
            className="w-full px-3 py-2 text-left hover:bg-[#f8f7f3] transition-colors"
          >
            <div className="flex items-start gap-2">
              {/* Rank */}
              <span
                className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[9px] font-bold text-white"
                style={{ backgroundColor: p.tier_color }}
              >
                {p.rank}
              </span>

              <div className="flex-1 min-w-0">
                {/* Name + tier */}
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] font-bold text-[#1b1c17] truncate">{p.name}</span>
                  <span
                    className="shrink-0 rounded px-1 py-0.5 text-[7px] font-bold text-white"
                    style={{ backgroundColor: p.tier_color }}
                  >
                    {p.tier}
                  </span>
                  {p.escalated && (
                    <span className="shrink-0 rounded bg-[#ba1a1a]/10 px-1 py-0.5 text-[7px] font-bold text-[#ba1a1a]">
                      ESC
                    </span>
                  )}
                </div>

                {/* Metrics row */}
                <div className="mt-0.5 flex items-center gap-2 text-[8px] text-[#707973]">
                  <span>Risk: <span className="font-bold" style={{ color: p.slope_state_color }}>{(p.risk_score * 100).toFixed(0)}%</span></span>
                  <span>Pop: <span className="font-bold text-[#1b1c17]">{p.population.toLocaleString()}</span></span>
                  <span>Urgency: <span className="font-bold text-[#1b1c17]">{(p.urgency_score * 100).toFixed(0)}%</span></span>
                </div>

                {/* Access + response */}
                <div className="mt-0.5 flex items-center gap-2">
                  <span className="rounded px-1 py-0.5 text-[7px] font-bold" style={{ backgroundColor: p.evac_color + "15", color: p.evac_color }}>
                    {p.evac_status}
                  </span>
                  <span className="text-[7px] text-[#707973]">
                    Response: {p.response_time}
                  </span>
                  <span className="rounded px-1 py-0.5 text-[7px] font-bold" style={{ backgroundColor: p.slope_state_color + "15", color: p.slope_state_color }}>
                    {p.slope_state_label}
                  </span>
                </div>
              </div>

              {/* Urgency gauge */}
              <div className="w-12 shrink-0">
                <div className="text-right text-[7px] text-[#707973]">
                  {(p.urgency_score * 100).toFixed(0)}%
                </div>
                <div className="mt-0.5 h-1.5 w-full rounded-full bg-[#e4e3db]">
                  <div
                    className="h-1.5 rounded-full transition-all duration-500"
                    style={{ width: `${p.urgency_score * 100}%`, backgroundColor: p.tier_color }}
                  />
                </div>
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Methodology note */}
      <div className="border-t border-[#e4e3db] bg-[#f8f7f3] px-3 py-1.5">
        <p className="text-[7px] text-[#707973]">
          Priority = 40% risk + 25% population exposure + 20% road inaccessibility + 15% SAR change.
          Response times are estimates for demo purposes.
        </p>
      </div>
    </div>
  );
}

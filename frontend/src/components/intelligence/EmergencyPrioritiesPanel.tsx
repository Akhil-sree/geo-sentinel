import { useEffect, useState } from "react";
import { getEmergencyPriorities } from "../../api/risk";
import { useUIStore } from "../../store/uiStore";
import { fmtPctOpt } from "../../lib/format";
import Spinner from "../common/Spinner";
import type { EmergencyPriority } from "../../types/risk";

export default function EmergencyPrioritiesPanel() {
  const simTime = useUIStore((s) => s.simTime);
  const [priorities, setPriorities] = useState<EmergencyPriority[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getEmergencyPriorities(simTime)
      .then((data) => setPriorities(data.priorities || []))
      .catch(() => setPriorities([]))
      .finally(() => setLoading(false));
  }, [simTime]);

  if (loading) {
    return (
      <div className="rounded-card p-4" style={{ background: 'rgba(229, 233, 224, 0.45)', backdropFilter: 'blur(8px)', border: '1px solid rgba(255,255,255,0.18)' }}>
        <div className="flex items-center gap-2 text-[14px] text-gs-text-secondary"><Spinner /> Loading priorities...</div>
      </div>
    );
  }

  if (!priorities.length) return null;

  const critical = priorities.filter((p) => p.tier === "CRITICAL");
  const high = priorities.filter((p) => p.tier === "HIGH");

  return (
    <div className="rounded-card p-4" style={{ background: 'rgba(229, 233, 224, 0.45)', backdropFilter: 'blur(8px)', border: '1px solid rgba(255,255,255,0.18)' }}>
      <h3 className="text-[15px] font-bold text-gs-text mb-1">Emergency Response Priorities</h3>
      <p className="text-[12px] text-gs-text-secondary mb-3">{priorities.length} zones ranked by urgency</p>

      {/* Summary badges */}
      <div className="flex gap-2 mb-3">
        <span className="px-2 py-1 rounded-full text-[11px] font-bold text-white" style={{ background: '#ba1a1a' }}>
          {critical.length} CRITICAL
        </span>
        <span className="px-2 py-1 rounded-full text-[11px] font-bold text-white" style={{ background: '#ea580c' }}>
          {high.length} HIGH
        </span>
      </div>

      {/* Priority list */}
      <div className="space-y-2">
        {priorities.map((p) => (
          <div key={p.zone_id} className="rounded-lg p-3" style={{ background: 'rgba(255,255,255,0.35)', borderLeft: `3px solid ${p.tier_color}` }}>
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <span className="text-[14px] font-bold text-gs-text">#{p.rank}</span>
                <span className="text-[13px] font-semibold text-gs-text">{p.name}</span>
              </div>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold text-white" style={{ background: p.tier_color }}>
                {p.tier}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2 text-[11px] mt-2">
              <div>
                <span className="text-gs-text-secondary">Risk</span>
                <div className="font-bold text-gs-text">{fmtPctOpt(p.risk_score)}</div>
              </div>
              <div>
                <span className="text-gs-text-secondary">Population</span>
                <div className="font-bold text-gs-text">{p.population.toLocaleString()}</div>
              </div>
              <div>
                <span className="text-gs-text-secondary">Response</span>
                <div className="font-bold text-gs-text">{p.response_time}</div>
              </div>
            </div>
            <div className="flex items-center gap-2 mt-2">
              <span className="px-2 py-0.5 rounded-full text-[10px] font-medium" style={{ background: p.evac_color + '20', color: p.evac_color }}>
                {p.evac_status}
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-medium" style={{ background: p.slope_state_color + '20', color: p.slope_state_color }}>
                {p.slope_state_label}
              </span>
              {p.escalated && <span className="px-2 py-0.5 rounded-full text-[10px] font-bold text-white bg-red-700">Escalated</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

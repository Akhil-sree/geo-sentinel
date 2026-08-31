import SeverityBadge from "../common/SeverityBadge";
import ModelVersionChip from "../common/ModelVersionChip";
import type { ZoneRisk } from "../../types/risk";

export default function RiskHeader({ risk }: { risk: ZoneRisk }) {
  return (
    <div className="flex items-start justify-between">
      <div>
        <h2 className="text-base font-bold">{risk.name}</h2>
        <p className="text-xs text-slate-500">{risk.district}</p>
        <div className="mt-1"><ModelVersionChip versions={risk.model_versions} /></div>
      </div>
      <div className="text-right">
        <SeverityBadge severity={risk.severity} large />
        <p className="mt-1 font-mono text-xs text-slate-500">
          score {risk.risk_score.toFixed(2)}
          {risk.escalated && <span className="ml-1 text-orange-400">▲ESC</span>}
        </p>
      </div>
    </div>
  );
}

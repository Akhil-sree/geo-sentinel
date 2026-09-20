import SeverityBadge from "../common/SeverityBadge";
import ModelVersionChip from "../common/ModelVersionChip";
import { fmtNum } from "../../lib/format";
import type { ZoneRisk } from "../../types/risk";

export default function RiskHeader({ risk }: { risk: ZoneRisk }) {
  return (
    <div className="flex items-start justify-between">
      <div>
        <h2 className="text-[14px] font-semibold text-gs-text">{risk.name}</h2>
        <p className="text-[11px] text-gs-text-secondary">{risk.district}</p>
        <div className="mt-1"><ModelVersionChip versions={risk.model_versions} /></div>
      </div>
      <div className="text-right">
        <SeverityBadge severity={risk.severity} large />
        <p className="mt-1 text-[10px] text-gs-text-secondary">
          score {fmtNum(risk.risk_score)}
          {risk.escalated && <span className="ml-1 text-risk-critical font-medium">▲ESC</span>}
        </p>
      </div>
    </div>
  );
}

import { SEV_COLOR, SEV_LABEL, SEV_DESCRIPTION, SEV_ACTION, SEV_ICON } from "../../lib/severity";
import type { Severity } from "../../types/risk";

export default function SeverityBadge({ severity, large = false, showDetails = false }: {
  severity: Severity; large?: boolean; showDetails?: boolean;
}) {
  return (
    <div className="inline-flex flex-col gap-1">
      <span
        className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 font-bold ring-1 ${large ? "text-sm" : "text-xs"}`}
        style={{
          background: `${SEV_COLOR[severity]}15`,
          color: SEV_COLOR[severity],
          border: `1.5px solid ${SEV_COLOR[severity]}40`,
        }}
      >
        <span className="text-[10px]">{SEV_ICON[severity]}</span>
        {SEV_LABEL[severity]}
      </span>
      {showDetails && (
        <div className="mt-0.5 rounded border px-2 py-1.5 text-[8px] leading-relaxed" style={{ borderColor: `${SEV_COLOR[severity]}30`, backgroundColor: `${SEV_COLOR[severity]}08` }}>
          <p className="font-bold" style={{ color: SEV_COLOR[severity] }}>{SEV_DESCRIPTION[severity]}</p>
          <p className="mt-0.5 text-[#707973]">Action: {SEV_ACTION[severity]}</p>
        </div>
      )}
    </div>
  );
}

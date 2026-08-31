import { SEV_COLOR, SEV_LABEL } from "../../lib/severity";
import type { Severity } from "../../types/risk";

export default function SeverityBadge({ severity, large = false }: {
  severity: Severity; large?: boolean;
}) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5
        font-semibold ${large ? "text-base" : "text-xs"}`}
      style={{ background: `${SEV_COLOR[severity]}22`, color: SEV_COLOR[severity],
               border: `1px solid ${SEV_COLOR[severity]}55` }}>
      <i className="h-2 w-2 rounded-full" style={{ background: SEV_COLOR[severity] }} />
      {SEV_LABEL[severity]}
    </span>
  );
}

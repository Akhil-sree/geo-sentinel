import { useEffect, useState } from "react";
import { getZoneEvidence } from "../../api/risk";
import { useUIStore } from "../../store/uiStore";
import SlopeStateBadge from "../common/SlopeStateBadge";
import SARComparison from "./SARComparison";
import type { ZoneEvidence } from "../../types/risk";

const ACTION_COLORS: Record<string, string> = {
  Escalate: "#ba1a1a",
  "Issue advisory": "#ea580c",
  "Verify locally": "#d97706",
  Monitor: "#245c45",
};

export default function CriticalSlopeCard() {
  const [evidence, setEvidence] = useState<ZoneEvidence | null>(null);
  const [loading, setLoading] = useState(false);
  const simTime = useUIStore((s) => s.simTime);
  const selectedZoneId = useUIStore((s) => s.selectedZoneId);

  useEffect(() => {
    if (!selectedZoneId) { setEvidence(null); return; }
    setLoading(true);
    getZoneEvidence(selectedZoneId, simTime)
      .then(setEvidence)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [selectedZoneId, simTime]);

  if (!selectedZoneId || loading || !evidence) return null;

  const st = evidence.slope_state;
  const isHighConcern = st.state === "CRITICAL" || st.state === "DEGRADING";

  return (
    <div className={`rounded border p-3 shadow-sm ${
      isHighConcern ? "border-[#ba1a1a]/30 bg-white" : "border-[#e4e3db] bg-white"
    }`}>

      {/* Header */}
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isHighConcern && <span className="text-sm">&#9888;</span>}
          <h3 className="text-[10px] font-bold uppercase tracking-wide text-[#1b1c17]">
            {isHighConcern ? "Emerging Instability" : "Slope Assessment"}
          </h3>
        </div>
        <SlopeStateBadge state={st.state} label={st.label} size="sm" />
      </div>

      {/* Location */}
      <p className="mb-2 text-[10px] text-[#404943]">
        {evidence.name}, {evidence.district}
      </p>

      {/* Key metrics grid */}
      <div className="mb-2 grid grid-cols-2 gap-1.5">
        <MetricBox label="SUSCEPTIBILITY" value={`${(evidence.static_score * 100).toFixed(0)}%`} high={evidence.static_score > 0.6} />
        <MetricBox label="TEMPORAL RISK" value={`${(evidence.dynamic_score * 100).toFixed(0)}%`} high={evidence.dynamic_score > 0.6} />
        <MetricBox label="72H RAINFALL" value={`${evidence.rainfall["72h"].toFixed(0)} mm`} high={evidence.rainfall["72h"] > 200} />
        <MetricBox label="SOIL MOISTURE" value={evidence.soil_moisture > 0.55 ? "SATURATED" : evidence.soil_moisture > 0.40 ? "MOIST" : "NORMAL"} high={evidence.soil_moisture > 0.55} />
      </div>

      {/* Slope stress bar */}
      <div className="mb-2 rounded bg-[#f0eee6] p-2">
        <div className="flex justify-between text-[8px] mb-1">
          <span className="font-bold text-[#404943]">SLOPE STRESS INDEX</span>
          <span className="font-bold" style={{ color: st.color }}>{(st.stress_score * 100).toFixed(0)}%</span>
        </div>
        <div className="h-2.5 w-full rounded-full bg-gray-200 overflow-hidden">
          <div className="h-full rounded-full transition-all duration-1000" style={{
            width: `${st.stress_score * 100}%`,
            background: `linear-gradient(90deg, #245c45, #d97706, ${st.color})`,
          }} />
        </div>
        <div className="flex justify-between text-[7px] text-[#707973] mt-0.5">
          <span>Stable</span>
          <span>Stressed</span>
          <span>Degrading</span>
          <span>Critical</span>
        </div>
      </div>

      {/* Terrain info */}
      {evidence.terrain && (
        <div className="mb-2 flex gap-3 text-[8px] text-[#707973]">
          <span>Slope: <b className="text-[#1b1c17]">{evidence.terrain.slope}&deg;</b></span>
          <span>Elevation: <b className="text-[#1b1c17]">{evidence.terrain.elevation}m</b></span>
        </div>
      )}

      {/* SAR evidence */}
      {evidence.sar && (
        <div className="mb-2">
          <SARComparison
            acquisitionDate={evidence.sar.acquisition_date}
            previousDate={evidence.sar.previous_acquisition_date}
            changeScore={evidence.sar.change_score}
            honestyNote={evidence.sar.honesty_note}
          />
        </div>
      )}

      {/* Evidence factors */}
      <div className="mb-2">
        <p className="mb-1 text-[8px] font-bold uppercase text-[#707973]">Why It Matters</p>
        <ul className="space-y-0.5">
          {evidence.explanation.factors.map((f, i) => (
            <li key={i} className="text-[9px] text-[#404943]">
              <span className="mr-1 text-[#04442f]">&#8226;</span> {f}
            </li>
          ))}
        </ul>
      </div>

      {/* Conclusion */}
      <div className="rounded bg-[#f0eee6] p-2 text-[9px] leading-relaxed text-[#404943]">
        <span className="font-bold">Conclusion: </span>
        {evidence.explanation.conclusion}
      </div>

      {/* Recommended action */}
      <div className="mt-2 flex items-center justify-between rounded border border-[#e4e3db] p-1.5">
        <span className="text-[8px] font-bold text-[#707973]">RECOMMENDED ACTION</span>
        <span
          className="rounded px-2 py-0.5 text-[9px] font-bold text-white"
          style={{ backgroundColor: ACTION_COLORS[evidence.explanation.recommended_action] ?? "#707973" }}
        >
          {evidence.explanation.recommended_action}
        </span>
      </div>

      {/* Honesty note */}
      <p className="mt-1.5 text-[7px] text-[#92400e]">
        Assessment based on model outputs, not confirmed field observation.
      </p>
    </div>
  );
}

function MetricBox({ label, value, high }: { label: string; value: string; high: boolean }) {
  return (
    <div className="rounded bg-[#f0eee6] p-1.5">
      <p className="text-[7px] font-bold tracking-wide text-[#707973]">{label}</p>
      <p className={`text-sm font-bold ${high ? "text-[#ba1a1a]" : "text-[#04442f]"}`}>
        {value}
      </p>
    </div>
  );
}

import { useEffect, useState } from "react";
import { getZoneEvidence } from "../../api/risk";
import { useUIStore } from "../../store/uiStore";
import { useI18n } from "../../lib/i18n";
import { fmtPctOpt, fmtMmOpt } from "../../lib/format";
import SlopeStateBadge from "../common/SlopeStateBadge";
import SARComparison from "./SARComparison";
import type { ZoneEvidence } from "../../types/risk";

const ACTION_KEY_MAP: Record<string, string> = {
  Escalate: "action.escalate",
  "Issue advisory": "action.issueAdvisory",
  "Verify locally": "action.verifyLocally",
  Monitor: "action.monitor",
};

const ACTION_COLORS: Record<string, string> = {
  Escalate: "bg-risk-critical text-white",
  "Issue advisory": "bg-risk-high text-white",
  "Verify locally": "bg-risk-moderate text-white",
  Monitor: "bg-risk-low text-white",
};

export default function CriticalSlopeCard() {
  const [evidence, setEvidence] = useState<ZoneEvidence | null>(null);
  const [loading, setLoading] = useState(false);
  const simTime = useUIStore((s) => s.simTime);
  const selectedZoneId = useUIStore((s) => s.selectedZoneId);
  const { t } = useI18n();

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
    <div className="rounded-lg p-4" style={{
      background: isHighConcern ? '#FFF5F5' : '#FFFFFF',
      border: isHighConcern ? '1px solid rgba(185, 28, 28, 0.18)' : '1px solid #E5E7EB',
    }}>

      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-[16px] font-semibold text-gs-text">
            {isHighConcern ? t("slope.instabilityDetected") : t("slope.assessment")}
          </h3>
          <p className="mt-1 text-[13px] text-gs-text-secondary">
            {evidence.name}, {evidence.district}
          </p>
        </div>
        <SlopeStateBadge state={st.state} label={st.label} size="md" />
      </div>

      {/* Key metrics grid */}
      <div className="mb-4 grid grid-cols-2 gap-3">
        <MetricBox
          label={t("slope.susceptibility")}
          value={fmtPctOpt(evidence.static_score)}
          high={(evidence.static_score ?? 0) > 0.6}
          tooltip={t("tooltip.susceptibility")}
        />
        <MetricBox
          label={t("slope.recentRisk")}
          value={fmtPctOpt(evidence.dynamic_score)}
          high={(evidence.dynamic_score ?? 0) > 0.6}
          tooltip={t("tooltip.recentRisk")}
        />
        <MetricBox
          label={t("slope.rainfall72h")}
          value={fmtMmOpt(evidence.rainfall?.["72h"])}
          high={(evidence.rainfall?.["72h"] ?? 0) > 200}
        />
        <MetricBox
          label={t("slope.soilMoisture")}
          value={typeof evidence.soil_moisture !== "number" ? "—" : evidence.soil_moisture > 0.55 ? t("soil.saturated") : evidence.soil_moisture > 0.40 ? t("soil.moist") : t("soil.normal")}
          high={(evidence.soil_moisture ?? 0) > 0.55}
        />
      </div>

      {/* Slope Stress Index */}
      <div className="mb-4 rounded-lg p-4" style={{
        background: '#F4F1EB',
      }}>
        <div className="flex justify-between items-center mb-3">
          <span className="text-[14px] font-medium text-gs-text">
            {t("slope.stressIndex")}
          </span>
          <span className="text-[15px] font-semibold" style={{ color: st.color }}>
            {fmtPctOpt(st.stress_score)}
          </span>
        </div>

        {/* Risk scale bar */}
        <div className="relative">
          <div className="h-3 w-full rounded-full bg-gs-border overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{
                width: `${st.stress_score * 100}%`,
                background: `linear-gradient(90deg, #2563EB, #D19217, #E76016, ${st.color})`,
              }}
            />
          </div>
          <div className="flex justify-between mt-1.5">
            <span className="text-[11px] text-gs-text-secondary">{t("slope.stable")}</span>
            <span className="text-[11px] text-gs-text-secondary">{t("slope.stressed")}</span>
            <span className="text-[11px] text-gs-text-secondary">{t("slope.degrading")}</span>
            <span className="text-[11px] text-gs-text-secondary">{t("slope.critical")}</span>
          </div>
        </div>
      </div>

      {/* Terrain info */}
      {evidence.terrain && (
        <div className="mb-4 flex gap-5 text-[13px] text-gs-text-secondary">
          <span>Slope: <b className="text-gs-text">{evidence.terrain.slope}°</b></span>
          <span>Elevation: <b className="text-gs-text">{evidence.terrain.elevation}m</b></span>
        </div>
      )}

      {/* SAR evidence */}
      {evidence.sar && (
        <div className="mb-4">
          <SARComparison
            acquisitionDate={evidence.sar.acquisition_date}
            previousDate={evidence.sar.previous_acquisition_date}
            changeScore={evidence.sar.change_score}
            honestyNote={evidence.sar.honesty_note}
          />
        </div>
      )}

      {/* Evidence factors */}
      <div className="mb-4">
        <p className="mb-2 text-[14px] font-medium text-gs-text-secondary">{t("slope.keyFactors")}</p>
        <ul className="space-y-1.5">
          {evidence.explanation.factors.map((f, i) => (
            <li key={i} className="flex items-start gap-2 text-[13px] text-gs-text">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-forest" />
              {f}
            </li>
          ))}
        </ul>
      </div>

      {/* Conclusion */}
      <div className="mb-4 rounded-lg p-4 text-[13px] leading-relaxed text-gs-text" style={{
        background: '#F4F1EB',
      }}>
        <span className="font-semibold">{t("slope.summary")} </span>
        {evidence.explanation.conclusion}
      </div>

      {/* Recommended action */}
      <div className="flex items-center justify-between rounded-lg p-3" style={{
        background: '#EDE8D9',
        border: '1px solid #D6D3CA',
      }}>
        <span className="text-[14px] font-medium text-gs-text-secondary">{t("slope.recommendedAction")}</span>
        <span className={`rounded px-3 py-1.5 text-[13px] font-semibold ${ACTION_COLORS[evidence.explanation.recommended_action] ?? "bg-gs-border text-gs-text-secondary"}`}>
          {t(ACTION_KEY_MAP[evidence.explanation.recommended_action] ?? "")}
        </span>
      </div>

      {/* Honesty note */}
      <p className="mt-3 text-[12px] italic text-gs-text-secondary">
        {t("slope.honesty")}
      </p>
    </div>
  );
}

function MetricBox({ label, value, high, tooltip }: { label: string; value: string; high: boolean; tooltip?: string }) {
  const [showTooltip, setShowTooltip] = useState(false);
  return (
    <div className="rounded-lg p-3" style={{
      background: '#F4F1EB',
    }}>
      <div className="flex items-center gap-1 mb-1">
        <p className="text-[13px] font-medium text-gs-text-secondary">{label}</p>
        {tooltip && (
          <span className="relative">
            <button
              type="button"
              className="text-[11px] text-gs-text-secondary/50 hover:text-gs-text-secondary transition-colors"
              onMouseEnter={() => setShowTooltip(true)}
              onMouseLeave={() => setShowTooltip(false)}
              onClick={() => setShowTooltip(!showTooltip)}
            >
              ⓘ
            </button>
            {showTooltip && (
              <span className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 rounded-lg px-3 py-2 text-[11px] leading-relaxed shadow-lg" style={{
                background: '#061611',
                border: '1px solid #1A3A2A',
                color: '#E8E6E1',
              }}>
                {tooltip}
              </span>
            )}
          </span>
        )}
      </div>
      <p className={`text-[18px] font-semibold ${high ? "text-risk-critical" : "text-forest"}`}>
        {value}
      </p>
    </div>
  );
}

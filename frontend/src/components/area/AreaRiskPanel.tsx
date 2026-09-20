import { useState } from "react";
import { useI18n } from "../../lib/i18n";
import { fmtNum, fmtMmOpt } from "../../lib/format";
import type { ZoneRisk } from "../../types/risk";

function severityLabelKey(sev: string): string {
  switch (sev) {
    case "VERY_HIGH": return "sev.critical";
    case "HIGH": return "sev.high";
    case "MODERATE": return "sev.moderate";
    default: return "sev.low";
  }
}

function severityBarColor(sev: string): string {
  switch (sev) {
    case "VERY_HIGH": return "#B4232B";
    case "HIGH": return "#E76016";
    case "MODERATE": return "#D19217";
    default: return "#2563EB";
  }
}

function responsePriorityKey(risk: ZoneRisk): string {
  if (risk.severity === "VERY_HIGH") return "priority.immediate";
  if (risk.severity === "HIGH") return "priority.highPriority";
  if (risk.severity === "MODERATE") return "priority.watch";
  return "priority.routine";
}

function responsePriorityStyle(risk: ZoneRisk): { color: string; bgColor: string } {
  if (risk.severity === "VERY_HIGH") return { color: "text-white", bgColor: "bg-risk-critical" };
  if (risk.severity === "HIGH") return { color: "text-white", bgColor: "bg-risk-high" };
  if (risk.severity === "MODERATE") return { color: "text-risk-moderate", bgColor: "bg-amber-50" };
  return { color: "text-risk-low", bgColor: "bg-emerald-50" };
}

function soilMoistureLabelKey(sm: number): string {
  if (sm > 0.45) return "soil.saturated";
  if (sm > 0.3) return "soil.moist";
  return "soil.normal";
}

function soilMoistureColor(sm: number): string {
  if (sm > 0.45) return "#B4232B";
  if (sm > 0.3) return "#D19217";
  return "#2563EB";
}

function TooltipIcon({ text }: { text: string }) {
  const [show, setShow] = useState(false);
  return (
    <span className="relative inline-flex ml-1">
      <button
        type="button"
        className="text-[13px] text-gs-text-secondary/60 hover:text-gs-text-secondary transition-colors"
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        onClick={() => setShow(!show)}
      >
        ⓘ
      </button>
      {show && (
        <span className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-52 rounded-lg px-3 py-2 text-[13px] leading-relaxed shadow-lg" style={{
          background: '#061611',
          border: '1px solid #1A3A2A',
          color: '#E8E6E1',
        }}>
          {text}
        </span>
      )}
    </span>
  );
}

/** Compact evidence bar */
function EvidenceBar({ frac, color }: { frac: number | null; color: string }) {
  return (
    <div className="gs-evidence-bar" style={{ height: 4 }}>
      <div
        className="gs-evidence-bar-fill"
        style={{
          width: `${frac === null ? 0 : Math.min(100, frac * 100)}%`,
          background: color,
        }}
      />
    </div>
  );
}

export default function AreaRiskPanel({ risk }: { risk: ZoneRisk }) {
  const { t } = useI18n();
  const priorityStyle = responsePriorityStyle(risk);
  const normalizedScore =
    typeof risk.risk_score === "number" && Number.isFinite(risk.risk_score)
      ? risk.risk_score
      : null;
  const sm =
    typeof risk.soil_moisture === "number" && Number.isFinite(risk.soil_moisture)
      ? risk.soil_moisture
      : null;
  const moisturePercent = sm === null ? null : sm > 1 ? sm : sm * 100;
  const moistureKey = sm === null ? null : soilMoistureLabelKey(sm);
  const moistureCol = sm === null ? "#65736C" : soilMoistureColor(sm);
  const moistureLabel = moistureKey === null ? "—" : t(moistureKey);

  const lastUpdated = (() => {
    try {
      const d = new Date(risk.sim_time);
      return d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }) + " IST";
    } catch {
      return "—";
    }
  })();

  const num = (v: number | null | undefined) =>
    typeof v === "number" && Number.isFinite(v) ? v : null;
  const staticScore = num(risk.static_score);
  const rain24 = num(risk.rainfall_24h);
  const rain72 = num(risk.rainfall_72h);
  const rain7d = num(risk.rainfall_7d);

  const band = (v: number | null, hi: number, mid: number): string | null => {
    if (v === null) return null;
    if (v >= hi) return "High";
    if (v >= mid) return "Elevated";
    return "Moderate";
  };
  const terrainBand = band(staticScore, 0.6, 0.4);
  const rainBand = band(rain72, 220, 110);
  const rainFrac = rain72 === null ? null : Math.min(1, rain72 / 220);

  return (
    <section aria-label="Selected location">
      {/* Location header — institutional style */}
      <div className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="truncate text-[15px] font-bold uppercase tracking-wide text-gs-text">{risk.name}</h3>
            <p className="mt-0.5 text-[11px] text-gs-text-secondary">{risk.district} · Meghalaya</p>
          </div>
          <span className="flex shrink-0 items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide" style={{
            background: `${severityBarColor(risk.severity)}14`,
            color: severityBarColor(risk.severity),
            boxShadow: `inset 0 0 0 1px ${severityBarColor(risk.severity)}35`,
          }}>
            <span className="inline-block h-1.5 w-1.5 rounded-full" style={{ background: severityBarColor(risk.severity) }} aria-hidden />
            {t(severityLabelKey(risk.severity))}
          </span>
        </div>
        <p className="mt-1 font-mono text-[10px] text-gs-text-secondary/60">Updated · {lastUpdated}</p>
      </div>

      {/* Risk score — prominent */}
      <div className="pb-3">
        <div className="gs-label mb-1">Model-Generated Risk Score</div>
        <div className="flex items-baseline gap-1.5">
          <span className="text-[36px] font-bold leading-none tabular-nums" style={{ color: severityBarColor(risk.severity) }}>
            {normalizedScore === null ? "—" : fmtNum(normalizedScore)}
          </span>
          <span className="text-[13px] font-medium text-gs-text-secondary">/ 1.00</span>
        </div>
        <p className="mt-1 text-[11px] text-gs-text-secondary">
          {normalizedScore === null
            ? "Unavailable — no silent default shown."
            : "Advisory indicator (uncalibrated model output — not a probability)."}
        </p>
      </div>

      {/* Evidence — compact bars */}
      <div className="space-y-2.5 pb-3">
        <div className="gs-label mb-1">Evidence</div>

        {/* Terrain */}
        <div>
          <div className="mb-0.5 flex items-center justify-between text-[11px]">
            <span className="font-medium text-gs-text-secondary">Terrain</span>
            <span className="font-semibold text-gs-text">{terrainBand ?? "—"}{staticScore !== null && ` · ${fmtNum(staticScore)}`}</span>
          </div>
          <EvidenceBar frac={staticScore} color={severityBarColor(risk.severity)} />
        </div>

        {/* Rainfall 72h */}
        <div>
          <div className="mb-0.5 flex items-center justify-between text-[11px]">
            <span className="font-medium text-gs-text-secondary">Rainfall · 72h</span>
            <span className="font-semibold text-gs-text">{rainBand ?? "—"}{rain72 !== null && ` · ${fmtMmOpt(rain72)}`}</span>
          </div>
          <EvidenceBar frac={rainFrac} color="#2F6F9F" />
        </div>

        {/* Soil moisture */}
        <div>
          <div className="mb-0.5 flex items-center justify-between text-[11px]">
            <span className="font-medium text-gs-text-secondary">
              Soil moisture <TooltipIcon text={t("tooltip.soilMoisture")} />
            </span>
            <span className="font-semibold" style={{ color: moistureCol }}>{moistureLabel}{moisturePercent !== null && ` · ${moisturePercent.toFixed(0)}%`}</span>
          </div>
          <EvidenceBar frac={sm} color={moistureCol} />
        </div>

        {/* SAR */}
        <div className="flex items-center justify-between text-[11px]">
          <span className="font-medium text-gs-text-secondary">Sentinel-1 SAR</span>
          <span className="font-medium text-gs-text-secondary/60">— Unavailable</span>
        </div>
      </div>

      {/* Response priority + rainfall detail */}
      <div className="flex items-center justify-between pb-2">
        <span className="gs-label">{t("risk.responsePriority")}</span>
        <span className={`rounded px-2 py-0.5 text-[11px] font-bold ${priorityStyle.bgColor} ${priorityStyle.color}`}>
          {t(responsePriorityKey(risk))}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-1.5">
        {[
          { k: "24h", v: rain24 },
          { k: "72h", v: rain72 },
          { k: "7d", v: rain7d },
        ].map((r) => (
          <div key={r.k} className="rounded-md px-2 py-1.5 text-center" style={{ background: 'rgba(237,233,224,0.5)' }}>
            <p className="text-[9px] font-bold uppercase tracking-wide text-gs-text-secondary">{r.k}</p>
            <p className="text-[14px] font-bold tabular-nums text-gs-text">{r.v === null ? "—" : fmtMmOpt(r.v)}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

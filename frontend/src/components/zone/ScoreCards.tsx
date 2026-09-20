import type { ZoneRisk } from "../../types/risk";
import { fmtNum, fmtPctOpt, fmtMmOpt } from "../../lib/format";

function Card({ label, value, sub, accent }: {
  label: string; value: string; sub: string; accent: string;
}) {
  return (
    <div className="rounded-card p-2.5" style={{
      background: 'rgba(231, 228, 217, 0.70)',
      backdropFilter: 'blur(3px)',
      WebkitBackdropFilter: 'blur(3px)',
      border: '1px solid rgba(255, 255, 255, 0.28)',
      boxShadow: '0 1px 6px rgba(15, 35, 27, 0.03)',
    }}>
      <div className="text-[9px] font-medium text-gs-text-secondary">{label}</div>
      <div className={`font-semibold text-[14px] ${accent}`}>{value}</div>
      <div className="text-[9px] text-gs-text-secondary">{sub}</div>
    </div>
  );
}

const num = (v: number | null | undefined) =>
  typeof v === "number" && Number.isFinite(v) ? v : null;

export default function ScoreCards({ risk }: { risk: ZoneRisk }) {
  const rain72 = num(risk.rainfall_72h);
  return (
    <div className="grid grid-cols-3 gap-2">
      <Card label="Fused risk" value={fmtNum(num(risk.risk_score))}
            accent="text-forest" sub={risk.severity} />
      <Card label="RF static" value={fmtNum(num(risk.static_score))}
            accent="text-gs-text" sub="terrain" />
      <Card label="Mamba dynamic" value={fmtNum(num(risk.dynamic_score))}
            accent="text-risk-degrading" sub="temporal" />
      <Card label="24h rain" value={fmtMmOpt(num(risk.rainfall_24h))}
            accent="text-gs-text" sub={`72h: ${rain72 === null ? "—" : `${rain72.toFixed(0)}mm`}`} />
      <Card label="Soil moisture" value={fmtPctOpt(num(risk.soil_moisture))}
            accent="text-gs-text" sub="regional proxy" />
      <Card label="Confidence" value={fmtPctOpt(num(risk.confidence))}
            accent="text-gs-text" sub="uncalibrated model score" />
    </div>
  );
}

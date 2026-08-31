import type { ZoneRisk } from "../../types/risk";

function Card({ label, value, sub, accent }: {
  label: string; value: string; sub: string; accent: string;
}) {
  return (
    <div className="rounded border border-slate-800 bg-slate-900/60 p-2">
      <div className="text-[10px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`font-mono text-lg font-bold ${accent}`}>{value}</div>
      <div className="text-[10px] text-slate-500">{sub}</div>
    </div>
  );
}

export default function ScoreCards({ risk }: { risk: ZoneRisk }) {
  return (
    <div className="grid grid-cols-3 gap-2">
      <Card label="Fused risk" value={risk.risk_score.toFixed(2)}
            accent="text-sky-400" sub={risk.severity} />
      <Card label="RF static" value={risk.static_score.toFixed(2)}
            accent="text-slate-300" sub="terrain" />
      <Card label="Mamba dynamic" value={risk.dynamic_score.toFixed(2)}
            accent="text-orange-400" sub="temporal" />
      <Card label="24h rain" value={`${risk.rainfall_24h.toFixed(0)}mm`}
            accent="text-slate-200" sub={`72h: ${risk.rainfall_72h.toFixed(0)}mm`} />
      <Card label="Soil moisture" value={`${(risk.soil_moisture * 100).toFixed(0)}%`}
            accent="text-slate-200" sub="regional proxy" />
      <Card label="Confidence" value={`${(risk.confidence * 100).toFixed(0)}%`}
            accent="text-slate-200" sub="model probability" />
    </div>
  );
}

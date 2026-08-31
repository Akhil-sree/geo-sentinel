import { Area, AreaChart, Tooltip, XAxis, YAxis } from "recharts";
import type { RiskHistoryPoint } from "../../types/risk";

export default function HistoryChart({ history }: { history: RiskHistoryPoint[] }) {
  if (history.length === 0)
    return <p className="text-xs text-slate-500">No persisted risk history yet — play the event to populate.</p>;

  const data = history.map((h) => ({
    t: h.timestamp.slice(11, 16),
    fused: h.risk_score, static: h.static, dynamic: h.dynamic,
  }));

  return (
    <AreaChart width={360} height={120} data={data} margin={{ top: 4, right: 4, bottom: 0, left: 4 }}>
      <XAxis dataKey="t" tick={{ fill: "#64748b", fontSize: 9 }} />
      <YAxis domain={[0, 1]} width={28} tick={{ fill: "#64748b", fontSize: 9 }} />
      <Tooltip contentStyle={{ background: "#0d1526", border: "1px solid #1e293b", fontSize: 11 }} />
      <Area dataKey="fused" stroke="#38bdf8" fill="#38bdf822" strokeWidth={2} isAnimationActive={false} />
    </AreaChart>
  );
}

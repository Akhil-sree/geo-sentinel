import { Area, AreaChart, Tooltip, XAxis, YAxis } from "recharts";
import type { RiskHistoryPoint } from "../../types/risk";

export default function HistoryChart({ history }: { history: RiskHistoryPoint[] }) {
  if (history.length === 0)
    return <p className="text-[10px] text-gs-text-secondary">No persisted risk history yet — play the event to populate.</p>;

  const data = history.map((h) => ({
    t: h.timestamp.slice(11, 16),
    fused: h.risk_score, static: h.static, dynamic: h.dynamic,
  }));

  return (
    <AreaChart width={360} height={120} data={data} margin={{ top: 4, right: 4, bottom: 0, left: 4 }}>
      <XAxis dataKey="t" tick={{ fill: "#647269", fontSize: 9 }} />
      <YAxis domain={[0, 1]} width={28} tick={{ fill: "#647269", fontSize: 9 }} />
      <Tooltip contentStyle={{ background: "rgba(255, 255, 255, 0.92)", border: "1px solid rgba(255, 255, 255, 0.30)", borderRadius: 8, fontSize: 11, backdropFilter: "blur(4px)", WebkitBackdropFilter: "blur(4px)", boxShadow: "0 4px 14px rgba(15, 35, 27, 0.10)" }} />
      <Area dataKey="fused" stroke="#075240" fill="#075240" fillOpacity={0.1} strokeWidth={2} isAnimationActive={false} />
    </AreaChart>
  );
}

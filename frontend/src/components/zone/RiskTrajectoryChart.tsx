import { useEffect, useState } from "react";
import {
  AreaChart, Area, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine, CartesianGrid,
} from "recharts";
import { getRiskTrajectory } from "../../api/risk";
import type { TrajectoryPoint, TrajectoryInterpretation } from "../../types/risk";

const INTERP_LABELS: Record<string, string> = {
  RAPIDLY_INTENSIFYING: "RAPIDLY INTENSIFYING",
  GRADUALLY_INCREASING: "GRADUALLY INCREASING",
  DECREASING: "DECREASING",
  STABLE: "STABLE",
  VARIABLE: "VARIABLE",
  NO_DATA: "INSUFFICIENT DATA",
};

const INTERP_COLORS: Record<string, string> = {
  RAPIDLY_INTENSIFYING: "#ba1a1a",
  GRADUALLY_INCREASING: "#ea580c",
  DECREASING: "#245c45",
  STABLE: "#245c45",
  VARIABLE: "#d97706",
  NO_DATA: "#707973",
};

interface ChartPoint extends TrajectoryPoint {
  t: string;
}

export default function RiskTrajectoryChart({ zoneId }: { zoneId: string }) {
  const [data, setData] = useState<ChartPoint[]>([]);
  const [interp, setInterp] = useState<TrajectoryInterpretation>("NO_DATA");
  const [animIdx, setAnimIdx] = useState(-1);

  useEffect(() => {
    getRiskTrajectory(zoneId)
      .then((r) => {
        const trajectory = r.trajectory.map((p) => ({
          ...p,
          t: new Date(p.timestamp).getHours() + "h",
        }));
        setData(trajectory);
        setInterp(r.interpretation as TrajectoryInterpretation);
        // Animate points sequentially
        setAnimIdx(-1);
        trajectory.forEach((_, i) => {
          setTimeout(() => setAnimIdx(i), i * 80);
        });
      })
      .catch(() => {});
  }, [zoneId]);

  if (data.length === 0) return null;

  const lastPoint = data[data.length - 1];
  const firstPoint = data[0];
  const riskChange = lastPoint.risk_score - firstPoint.risk_score;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <p className="text-[10px] font-bold text-[#1b1c17]">
          RISK TRAJECTORY
        </p>
        <span
          className="rounded px-1.5 py-0.5 text-[8px] font-bold"
          style={{ color: INTERP_COLORS[interp], backgroundColor: `${INTERP_COLORS[interp]}15` }}
        >
          {INTERP_LABELS[interp]}
        </span>
      </div>

      {/* Risk progression display */}
      <div className="flex items-center gap-1 text-[9px]">
        {data.filter((_, i) => i % Math.max(1, Math.floor(data.length / 4)) === 0 || i === data.length - 1).map((p, i, arr) => (
          <div key={i} className="flex items-center">
            <span className={`font-bold ${i <= animIdx ? "animate-count" : "opacity-30"}`}
              style={{ color: p.severity === "VERY_HIGH" || p.severity === "HIGH" ? "#ba1a1a" : p.severity === "MODERATE" ? "#d97706" : "#245c45" }}>
              {(p.risk_score * 100).toFixed(0)}%
            </span>
            {i < arr.length - 1 && <span className="mx-0.5 text-gray-400">→</span>}
          </div>
        ))}
      </div>

      {/* Change indicator */}
      {Math.abs(riskChange) > 0.01 && (
        <p className="text-[8px] font-semibold" style={{ color: riskChange >= 0 ? "#ba1a1a" : "#245c45" }}>
          {riskChange >= 0 ? "↑" : "↓"} {(Math.abs(riskChange) * 100).toFixed(1)}% overall change
        </p>
      )}

      <div className="h-28 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e4e3db" />
            <XAxis dataKey="t" tick={{ fontSize: 7, fill: "#707973" }} interval={Math.floor(data.length / 4)} />
            <YAxis domain={[0, 1]} tick={{ fontSize: 7, fill: "#707973" }} width={22} />
            <Tooltip
              contentStyle={{ fontSize: 9, borderRadius: 4, border: "1px solid #d9e2d9" }}
              formatter={(v: any, name: string) => [
                v.toFixed(3),
                name === "risk" ? "Fused Risk" : name === "static" ? "Static (RF)" : "Dynamic (Mamba)",
              ]}
            />
            <ReferenceLine y={0.75} stroke="#ba1a1a" strokeDasharray="3 3" strokeOpacity={0.5} />
            <ReferenceLine y={0.50} stroke="#d97706" strokeDasharray="3 3" strokeOpacity={0.4} />
            <Area dataKey="risk" stroke="#ba1a1a" fill="#ba1a1a" fillOpacity={0.1} strokeWidth={1.5} dot={{ r: 2, fill: "#ba1a1a" }} />
            <Line dataKey="static" stroke="#245c45" strokeWidth={1} dot={false} strokeDasharray="4 2" />
            <Line dataKey="dynamic" stroke="#ea580c" strokeWidth={1} dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="flex gap-3 text-[8px] text-[#707973]">
        <span><i className="mr-1 inline-block h-1.5 w-3 rounded bg-[#ba1a1a]" /> Fused Risk</span>
        <span><i className="mr-1 inline-block h-1.5 w-3 rounded bg-[#245c45]" style={{ borderTop: "1px dashed #245c45" }} /> Static (RF)</span>
        <span><i className="mr-1 inline-block h-1.5 w-3 rounded bg-[#ea580c]" /> Dynamic (Mamba)</span>
      </div>
    </div>
  );
}

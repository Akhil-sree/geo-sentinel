import { useState, useEffect } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Legend,
} from "recharts";
import { getRiskTrajectory } from "../../api/risk";
import { getZoneHistory } from "../../api/risk";
import type { TrajectoryPoint } from "../../types/risk";

function fmtTime(iso: string): string {
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}h`;
}

export default function RiskTrajectoryChart({ zoneId }: { zoneId: string }) {
  const [data, setData] = useState<TrajectoryPoint[] | null>(null);
  const [animIdx, setAnimIdx] = useState(-1);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setAnimIdx(-1);
    getRiskTrajectory(zoneId)
      .then((r) => {
        if (cancelled) return;
        if (r.trajectory?.length) {
          setData(r.trajectory);
        } else {
          // Fallback: live history points (no stored slope-state yet)
          return getZoneHistory(zoneId).then((rows: any[]) => {
            if (cancelled) return;
            setData(rows.map((h) => ({
              timestamp: h.timestamp,
              risk_score: h.risk_score,
              static: h.static,
              dynamic: h.dynamic,
              severity: h.severity,
              escalated: h.escalated,
              slope_state: "STABLE" as const,
              slope_state_label: "Stable",
              slope_state_color: "#2563EB",
            })));
          });
        }
      })
      .catch(() => { if (!cancelled) setData([]); });
    return () => { cancelled = true; };
  }, [zoneId]);

  useEffect(() => {
    if (!data || !data.length) return;
    setAnimIdx(-1);
    const timers = data.map((_, i) => setTimeout(() => setAnimIdx(i), i * 80));
    return () => timers.forEach(clearTimeout);
  }, [data]);

  if (data === null) {
    return <p className="text-[13px] text-gs-text-secondary">Loading trajectory…</p>;
  }

  if (data.length === 0) {
    return (
      <div>
        <p className="text-[16px] font-medium text-gs-text">Risk trajectory</p>
        <p className="mt-1 text-[13px] text-gs-text-secondary">
          No trajectory yet — move the event scrubber to generate risk history for this zone.
        </p>
      </div>
    );
  }

  const chartData = data.map((d) => ({
    time: fmtTime(d.timestamp),
    fused: d.risk_score,
    rf: d.static,
    mamba: d.dynamic,
  }));

  const pcts = data.map((d) => Math.round(d.risk_score * 100) + "%");
  const riskChange = data[data.length - 1].risk_score - data[0].risk_score;
  const last = data[data.length - 1];
  const worsening = riskChange >= 0;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-[16px] font-medium text-gs-text">
          Risk trajectory
        </p>
        <span
          className="rounded px-2 py-0.5 text-[13px] font-medium"
          style={{ color: last.slope_state_color, backgroundColor: `${last.slope_state_color}12` }}
        >
          {last.slope_state_label} · {pcts[pcts.length - 1]}
        </span>
      </div>

      <div className="flex items-center gap-1.5 text-[14px] flex-wrap">
        {pcts.map((pct, i) => (
          <div key={i} className="flex items-center">
            <span
              className={`font-medium ${i <= animIdx ? "animate-count" : "opacity-30"}`}
              style={{ color: data[i].slope_state_color }}
              title={`${fmtTime(data[i].timestamp)} — ${data[i].slope_state_label}`}
            >
              {pct}
            </span>
            {i < pcts.length - 1 && <span className="mx-0.5 text-gs-border">→</span>}
          </div>
        ))}
      </div>

      {Math.abs(riskChange) > 0.01 && (
        <p className="text-[13px] font-medium" style={{ color: worsening ? "#E55A2B" : "#2563EB" }}>
          {worsening ? "↑" : "↓"} {(Math.abs(riskChange) * 100).toFixed(1)}% overall change
        </p>
      )}

      <div className="h-44 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
            <XAxis
              dataKey="time"
              tick={{ fontSize: 12, fill: "#9CA3AF" }}
              axisLine={{ stroke: "#E5E7EB" }}
              tickLine={false}
            />
            <YAxis
              domain={[0, 1]}
              tick={{ fontSize: 12, fill: "#9CA3AF" }}
              ticks={[0, 0.25, 0.5, 0.75, 1]}
              axisLine={false}
              tickLine={false}
              width={30}
            />
            <Tooltip
              formatter={(val: number) => val.toFixed(2)}
              contentStyle={{ fontSize: 13, borderRadius: 8, border: "1px solid rgba(255, 255, 255, 0.30)", background: "rgba(255, 255, 255, 0.92)", backdropFilter: "blur(4px)", WebkitBackdropFilter: "blur(4px)", boxShadow: "0 4px 14px rgba(15, 35, 27, 0.10)" }}
            />
            <Legend
              iconType="line"
              iconSize={12}
              wrapperStyle={{ fontSize: 13, paddingTop: 8 }}
            />
            <Line
              type="monotone"
              dataKey="fused"
              name="Fused Risk"
              stroke="#B91C1C"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
            <Line
              type="monotone"
              dataKey="rf"
              name="Static (RF)"
              stroke="#2563EB"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
            <Line
              type="monotone"
              dataKey="mamba"
              name="Dynamic (Mamba)"
              stroke="#E55A2B"
              strokeWidth={2}
              dot={false}
              strokeDasharray="4 2"
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

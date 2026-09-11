import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import { getZoneHistory } from "../../api/risk";

const THRESH = 0.6; // must match backend fusion threshold

export default function DynamicRiskChart({ zoneId }: { zoneId: string }) {
  const [data, setData] = useState<any[]>([]);

  useEffect(() => {
    getZoneHistory(zoneId)
      .then((rows) =>
        setData(rows.map((r: any) => ({
          t: new Date(r.timestamp).getHours() + "h",
          score: r.dynamic,
        }))))
      .catch(() => {});
  }, [zoneId]);

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
        <XAxis dataKey="t" tick={{ fontSize: 8, fill: "#707973" }} interval={23} />
        <YAxis domain={[0, 1]} tick={{ fontSize: 8, fill: "#707973" }} width={24} />
        <Tooltip contentStyle={{ fontSize: 10, borderRadius: 4, border: "1px solid #d9e2d9" }}
                 formatter={(v: any) => [v != null ? Number(v).toFixed(2) : "—", "dynamic"]} />
        <ReferenceLine y={THRESH} stroke="#ba1a1a" strokeDasharray="3 3"
                       strokeOpacity={0.6} />
        <Line dataKey="score" stroke="#ea580c" strokeWidth={1.5} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

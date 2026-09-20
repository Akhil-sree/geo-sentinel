import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import { getZoneHistory } from "../../api/risk";

const THRESH = 0.6;

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
        <XAxis dataKey="t" tick={{ fontSize: 8, fill: "#647269" }} interval={23} />
        <YAxis domain={[0, 1]} tick={{ fontSize: 8, fill: "#647269" }} width={24} />
        <Tooltip contentStyle={{ fontSize: 10, borderRadius: 8, border: "1px solid rgba(255, 255, 255, 0.30)", background: "rgba(255, 255, 255, 0.92)", backdropFilter: "blur(4px)", WebkitBackdropFilter: "blur(4px)", boxShadow: "0 4px 14px rgba(15, 35, 27, 0.10)" }}
                 formatter={(v: any) => [v.toFixed(2), "dynamic"]} />
        <ReferenceLine y={THRESH} stroke="#B4232B" strokeDasharray="3 3" strokeOpacity={0.6} />
        <Line dataKey="score" stroke="#E76016" strokeWidth={1.5} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

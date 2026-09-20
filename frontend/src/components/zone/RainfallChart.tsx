import { useEffect, useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { getZoneRainfall } from "../../api/risk";

interface RainfallPoint {
  t: string;
  mm: number;
}

interface RainfallChartProps {
  zoneId: string;
}

export default function RainfallChart({
  zoneId,
}: RainfallChartProps) {
  const [data, setData] = useState<RainfallPoint[]>([]);

  useEffect(() => {
    let cancelled = false;

    getZoneRainfall(zoneId)
      .then((response) => {
        if (cancelled) return;

        setData(
          (response.observations ?? []).map((r: any) => ({
            t: `${new Date(r.timestamp).getHours()}h`,
            mm: Number(r.rainfall_mm_per_hr) || 0,
          }))
        );
      })
      .catch(() => {
        if (!cancelled) {
          setData([]);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [zoneId]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="min-h-0 flex-1">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <XAxis dataKey="t" tick={{ fontSize: 8, fill: "#647269" }} interval={23} tickLine={false} axisLine={{ stroke: "#DCE3DD" }} />
            <YAxis tick={{ fontSize: 8, fill: "#647269" }} width={28} tickLine={false} axisLine={false} />
            <Tooltip
              contentStyle={{ fontSize: 10, borderRadius: 8, border: "1px solid rgba(255, 255, 255, 0.30)", background: "rgba(255, 255, 255, 0.92)", backdropFilter: "blur(4px)", WebkitBackdropFilter: "blur(4px)", boxShadow: "0 4px 14px rgba(15, 35, 27, 0.10)" }}
              formatter={(value) => [`${Number(value).toFixed(1)} mm/h`, "Rainfall"]}
              labelFormatter={(label) => `Time: ${label}`}
            />
            <Area type="monotone" dataKey="mm" stroke="#075240" fill="#075240" fillOpacity={0.15} strokeWidth={1.5} dot={false} activeDot={{ r: 3 }} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-1 shrink-0 rounded-card border border-risk-moderate/20 bg-risk-moderate/5 p-1.5 text-[9px] leading-snug text-risk-moderate">
        <strong>Simulated data</strong> — simulated IMD rainfall observations. Real ingestion swaps the adapter.
      </div>
    </div>
  );
}

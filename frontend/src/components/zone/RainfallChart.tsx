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

      {/* Chart */}
      <div className="min-h-0 flex-1">

        <ResponsiveContainer
          width="100%"
          height="100%"
        >
          <AreaChart
            data={data}
            margin={{
              top: 4,
              right: 4,
              bottom: 0,
              left: 0,
            }}
          >

            <XAxis
              dataKey="t"
              tick={{
                fontSize: 8,
                fill: "#707973",
              }}
              interval={23}
              tickLine={false}
              axisLine={{
                stroke: "#d9e2d9",
              }}
            />

            <YAxis
              tick={{
                fontSize: 8,
                fill: "#707973",
              }}
              width={28}
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => `${value}`}
            />

            <Tooltip
              contentStyle={{
                fontSize: 10,
                borderRadius: 4,
                border: "1px solid #d9e2d9",
              }}
              formatter={(value) => [
                `${Number(value).toFixed(1)} mm/h`,
                "Rainfall",
              ]}
              labelFormatter={(label) => `Time: ${label}`}
            />

            <Area
              type="monotone"
              dataKey="mm"
              stroke="#04442f"
              fill="#245c45"
              fillOpacity={0.25}
              strokeWidth={1.5}
              dot={false}
              activeDot={{
                r: 3,
              }}
            />

          </AreaChart>
        </ResponsiveContainer>

      </div>


      {/* Demo Notice */}
      <div className="mt-1 shrink-0 rounded border border-[#d9e2d9] bg-[#f6f4ec] p-1.5 text-[9px] leading-snug text-[#92400e]">
        <strong>DEMO DATA</strong> — simulated IMD rainfall
        observations. Real ingestion swaps the adapter; this
        chart and its contract stay identical.
      </div>

    </div>
  );
}

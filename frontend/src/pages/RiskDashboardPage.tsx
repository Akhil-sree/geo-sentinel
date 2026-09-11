import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { getSeveritySummary, type SeveritySummaryItem } from "../api/dashboard";
import { useUIStore } from "../store/uiStore";

const SEV_COLOR: Record<string, string> = {
  LOW: "#245c45",
  MODERATE: "#d97706",
  HIGH: "#ea580c",
  VERY_HIGH: "#ba1a1a",
};

const SEV_ICON: Record<string, string> = {
  LOW: "\u25CB",
  MODERATE: "\u25D4",
  HIGH: "\u25D1",
  VERY_HIGH: "\u26A0",
};

export default function RiskDashboardPage() {
  const [data, setData] = useState<{
    summary: Record<string, number>;
    zones: SeveritySummaryItem[];
    total_zones: number;
    total_population: number;
    exposed_population: number;
    escalated_count: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const selectZone = useUIStore((s) => s.selectZone);

  useEffect(() => {
    getSeveritySummary()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading || !data) {
    return (
      <div className="flex flex-1 items-center justify-center bg-[#f0eee6]">
        <div className="text-center">
          <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-[#04442f] border-t-transparent" />
          <p className="text-[11px] text-[#707973]">Loading severity summary...</p>
        </div>
      </div>
    );
  }

  const chartData = Object.entries(data.summary).map(([sev, count]) => ({
    severity: sev,
    count,
    color: SEV_COLOR[sev],
  }));

  return (
    <div className="flex flex-1 flex-col overflow-y-auto bg-[#f0eee6]">
      {/* Header */}
      <div className="border-b border-[#d9e2d9] bg-white px-5 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-[#04442f]">Risk Severity Dashboard</h1>
            <p className="text-[10px] text-[#707973]">
              Unified overview of zone-level risk across the North Eastern Region
            </p>
          </div>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-5 gap-3 px-5 py-3">
        <div className="rounded-lg border border-[#d9e2d9] bg-white p-3 shadow-sm">
          <p className="text-[8px] font-semibold uppercase text-[#707973]">Total Zones</p>
          <p className="text-2xl font-bold text-[#04442f]">{data.total_zones}</p>
        </div>
        <div className="rounded-lg border border-[#ba1a1a]/20 bg-[#ba1a1a]/5 p-3 shadow-sm">
          <p className="text-[8px] font-semibold uppercase text-[#ba1a1a]">Very High</p>
          <p className="text-2xl font-bold text-[#ba1a1a]">{data.summary.VERY_HIGH || 0}</p>
        </div>
        <div className="rounded-lg border border-[#ea580c]/20 bg-[#ea580c]/5 p-3 shadow-sm">
          <p className="text-[8px] font-semibold uppercase text-[#ea580c]">High</p>
          <p className="text-2xl font-bold text-[#ea580c]">{data.summary.HIGH || 0}</p>
        </div>
        <div className="rounded-lg border border-[#d97706]/20 bg-[#d97706]/5 p-3 shadow-sm">
          <p className="text-[8px] font-semibold uppercase text-[#d97706]">Moderate</p>
          <p className="text-2xl font-bold text-[#d97706]">{data.summary.MODERATE || 0}</p>
        </div>
        <div className="rounded-lg border border-[#245c45]/20 bg-[#245c45]/5 p-3 shadow-sm">
          <p className="text-[8px] font-semibold uppercase text-[#245c45]">Low</p>
          <p className="text-2xl font-bold text-[#245c45]">{data.summary.LOW || 0}</p>
        </div>
      </div>

      {/* Population + escalation row */}
      <div className="grid grid-cols-3 gap-3 px-5 pb-3">
        <div className="rounded-lg border border-[#d9e2d9] bg-white p-3 shadow-sm">
          <p className="text-[8px] font-semibold uppercase text-[#707973]">Total Population</p>
          <p className="text-xl font-bold text-[#1b1c17]">{data.total_population.toLocaleString()}</p>
        </div>
        <div className="rounded-lg border border-[#ba1a1a]/20 bg-[#ba1a1a]/5 p-3 shadow-sm">
          <p className="text-[8px] font-semibold uppercase text-[#ba1a1a]">Exposed Population (High + Very High)</p>
          <p className="text-xl font-bold text-[#ba1a1a]">{data.exposed_population.toLocaleString()}</p>
        </div>
        <div className="rounded-lg border border-[#d97706]/20 bg-[#d97706]/5 p-3 shadow-sm">
          <p className="text-[8px] font-semibold uppercase text-[#d97706]">Escalated Zones</p>
          <p className="text-xl font-bold text-[#d97706]">{data.escalated_count}</p>
        </div>
      </div>

      {/* Chart + Zone list */}
      <div className="grid grid-cols-3 gap-3 px-5 pb-5">
        {/* Bar chart */}
        <div className="col-span-1 rounded-lg border border-[#d9e2d9] bg-white p-4 shadow-sm">
          <h3 className="mb-3 text-[10px] font-bold uppercase tracking-wide text-[#1b1c17]">
            Severity Distribution
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData} barCategoryGap="20%">
              <XAxis
                dataKey="severity"
                tick={{ fontSize: 9, fill: "#707973" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 9, fill: "#707973" }}
                axisLine={false}
                tickLine={false}
                allowDecimals={false}
              />
              <Tooltip
                contentStyle={{ fontSize: 10, borderRadius: 8, border: "1px solid #d9e2d9" }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Zone detail list */}
        <div className="col-span-2 rounded-lg border border-[#d9e2d9] bg-white shadow-sm">
          <div className="border-b border-[#e4e3db] px-4 py-2.5">
            <h3 className="text-[10px] font-bold uppercase tracking-wide text-[#1b1c17]">
              Zone-Level Risk Detail
            </h3>
          </div>
          <div className="divide-y divide-[#e4e3db]">
            {/* Table header */}
            <div className="grid grid-cols-7 gap-2 bg-[#f8f7f3] px-4 py-1.5 text-[8px] font-bold uppercase text-[#707973]">
              <span className="col-span-2">Zone</span>
              <span>Risk</span>
              <span>Severity</span>
              <span>Pop.</span>
              <span>24h Rain</span>
              <span>Slope</span>
            </div>
            {data.zones.map((z) => {
              const sevColor = SEV_COLOR[z.severity] || "#707973";
              return (
                <button
                  key={z.zone_id}
                  onClick={() => selectZone(z.zone_id)}
                  className="grid w-full grid-cols-7 gap-2 px-4 py-2 text-left transition-colors hover:bg-[#f8f7f3]"
                >
                  <span className="col-span-2">
                    <span className="text-[10px] font-bold text-[#1b1c17]">{z.name}</span>
                    <br />
                    <span className="text-[8px] text-[#707973]">{z.district}</span>
                  </span>
                  <span className="text-[10px] font-bold" style={{ color: sevColor }}>
                    {(z.risk_score * 100).toFixed(0)}%
                  </span>
                  <span>
                    <span
                      className="inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[8px] font-bold"
                      style={{ backgroundColor: sevColor + "15", color: sevColor }}
                    >
                      {SEV_ICON[z.severity]} {z.severity}
                    </span>
                  </span>
                  <span className="text-[10px] font-semibold text-[#1b1c17]">
                    {z.population.toLocaleString()}
                  </span>
                  <span className="text-[10px] text-[#1b1c17]">
                    {z.rainfall_24h.toFixed(1)} mm
                  </span>
                  <span className="text-[10px] text-[#1b1c17]">
                    {z.slope}\u00B0
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

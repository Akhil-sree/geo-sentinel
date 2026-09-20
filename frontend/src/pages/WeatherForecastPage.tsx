import { useEffect, useState } from "react";
import { getWeatherOverview } from "../api/dashboard";
import { useUIStore } from "../store/uiStore";
import Spinner from "../components/common/Spinner";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import type { WeatherOverviewZone } from "../types/risk";

export default function WeatherForecastPage() {
  const simTime = useUIStore((s) => s.simTime);
  const [forecasts, setForecasts] = useState<WeatherOverviewZone[]>([]);
  const [extremeCount, setExtremeCount] = useState(0);
  const [highCount, setHighCount] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getWeatherOverview(simTime)
      .then((data) => {
        setForecasts(data.forecasts || []);
        setExtremeCount(data.extreme_count || 0);
        setHighCount(data.high_count || 0);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [simTime]);

  const chartData = forecasts.map((r) => ({
    name: r.name.split("(")[0].trim(),
    rainfall24h: +r.rainfall_24h.toFixed(1),
    rainfall72h: +r.rainfall_72h.toFixed(1),
    risk: +(r.risk_score * 100).toFixed(0),
  }));

  const escalatedCount = forecasts.filter((r) => r.escalated).length;

  return (
    <div className="flex flex-1 flex-col overflow-y-auto p-6" style={{ background: '#F4F5F0' }}>
      <div className="mx-auto w-full max-w-6xl">
        <div className="mb-6">
          <h1 className="text-[28px] font-bold" style={{ color: '#1A3C2E' }}>Weather & Rainfall Overview</h1>
          <p className="text-[14px] mt-1" style={{ color: '#6B7280' }}>Region-wide rainfall and environmental conditions across all monitoring zones</p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Spinner /><span className="ml-3 text-[16px]" style={{ color: '#6B7280' }}>Loading...</span>
          </div>
        ) : (
          <>
            {/* Alert Badges */}
            <div className="flex gap-3 mb-6 flex-wrap">
              {extremeCount > 0 && (
                <div className="flex items-center gap-2 rounded-full px-4 py-2" style={{ background: 'rgba(186,26,26,0.1)', border: '1px solid rgba(186,26,26,0.3)' }}>
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-60" style={{ background: '#ba1a1a' }} />
                    <span className="relative inline-flex h-2.5 w-2.5 rounded-full" style={{ background: '#ba1a1a' }} />
                  </span>
                  <span className="text-[13px] font-bold" style={{ color: '#ba1a1a' }}>{extremeCount} EXTREME RAINFALL</span>
                </div>
              )}
              {highCount > 0 && (
                <div className="flex items-center gap-2 rounded-full px-4 py-2" style={{ background: 'rgba(234,88,12,0.1)', border: '1px solid rgba(234,88,12,0.3)' }}>
                  <span className="text-[13px] font-bold" style={{ color: '#ea580c' }}>{highCount} HIGH RAINFALL</span>
                </div>
              )}
              {escalatedCount > 0 && (
                <div className="flex items-center gap-2 rounded-full px-4 py-2" style={{ background: 'rgba(217,119,6,0.1)', border: '1px solid rgba(217,119,6,0.3)' }}>
                  <span className="text-[13px] font-bold" style={{ color: '#d97706' }}>{escalatedCount} ESCALATED ZONES</span>
                </div>
              )}
            </div>

            {/* Rainfall Chart */}
            <div className="rounded-xl p-5 mb-6" style={{ background: '#FFFFFF', border: '1px solid #E5E7EB' }}>
              <h3 className="text-[16px] font-bold mb-4" style={{ color: '#1A3C2E' }}>24h Rainfall by Zone</h3>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={chartData}>
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} angle={-20} textAnchor="end" height={60} />
                  <YAxis tick={{ fontSize: 11 }} label={{ value: 'mm', position: 'insideTopLeft', fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{ background: '#fff', border: '1px solid #E5E7EB', borderRadius: 8, fontSize: 12 }}
                    formatter={(v: number, name: string) => [`${v} mm`, name === "rainfall24h" ? "24h Rainfall" : "72h Rainfall"]}
                  />
                  <Bar dataKey="rainfall24h" name="rainfall24h" radius={[4, 4, 0, 0]}>
                    {chartData.map((entry, i) => (
                       <Cell key={i} fill={entry.rainfall24h > 100 ? '#ba1a1a' : entry.rainfall24h > 50 ? '#ea580c' : entry.rainfall24h > 25 ? '#d97706' : '#2563EB'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Zone Cards */}
            <div className="grid grid-cols-2 gap-4">
              {forecasts.sort((a, b) => b.risk_score - a.risk_score).map((r) => {
                const sevColor = r.risk_color || '#999';
                let rainLevel = "LOW";
                let rainColor = "#2563EB";
                let rainMsg = "No significant rainfall";
                if (r.rainfall_24h > 100) { rainLevel = "EXTREME"; rainColor = "#ba1a1a"; rainMsg = "Heavy rainfall warning — flash flood risk"; }
                else if (r.rainfall_24h > 50) { rainLevel = "HIGH"; rainColor = "#ea580c"; rainMsg = "Moderate to heavy rainfall expected"; }
                else if (r.rainfall_24h > 25) { rainLevel = "MODERATE"; rainColor = "#d97706"; rainMsg = "Light to moderate rainfall"; }

                return (
                  <div key={r.zone_id} className="rounded-xl p-4" style={{ background: '#FFFFFF', border: '1px solid #E5E7EB', borderLeft: `4px solid ${sevColor}` }}>
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <h4 className="text-[16px] font-bold" style={{ color: '#1A3C2E' }}>{r.name}</h4>
                        <p className="text-[12px]" style={{ color: '#6B7280' }}>{r.district}</p>
                      </div>
                      <span className="px-3 py-1 rounded-full text-[12px] font-bold text-white" style={{ background: rainColor }}>{rainLevel}</span>
                    </div>
                    <p className="text-[13px] mb-3" style={{ color: '#6B7280' }}>{r.message || rainMsg}</p>
                    <div className="grid grid-cols-4 gap-3">
                      <div>
                        <div className="text-[11px]" style={{ color: '#6B7280' }}>Rain 24h</div>
                        <div className="text-[15px] font-bold" style={{ color: '#1A3C2E' }}>{r.rainfall_24h.toFixed(1)} mm</div>
                      </div>
                      <div>
                        <div className="text-[11px]" style={{ color: '#6B7280' }}>Rain 72h</div>
                        <div className="text-[15px] font-bold" style={{ color: '#1A3C2E' }}>{r.rainfall_72h.toFixed(1)} mm</div>
                      </div>
                      <div>
                        <div className="text-[11px]" style={{ color: '#6B7280' }}>Soil</div>
                        <div className="text-[15px] font-bold" style={{ color: r.soil_moisture > 0.7 ? '#ba1a1a' : '#1A3C2E' }}>{(r.soil_moisture * 100).toFixed(0)}%</div>
                      </div>
                      <div>
                        <div className="text-[11px]" style={{ color: '#6B7280' }}>Risk</div>
                        <div className="text-[15px] font-bold" style={{ color: sevColor }}>{(r.risk_score * 100).toFixed(0)}%</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold text-white" style={{ background: sevColor }}>{r.risk_level || r.severity?.replace("_", " ")}</span>
                      {r.escalated && <span className="px-2 py-0.5 rounded-full text-[10px] font-bold text-white" style={{ background: '#ba1a1a' }}>ESCALATED</span>}
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

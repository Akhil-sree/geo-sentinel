import { useEffect, useState } from "react";
import { getWeatherOverview } from "../../api/dashboard";
import { useUIStore } from "../../store/uiStore";
import { fmtPctOpt, fmtMmOpt } from "../../lib/format";
import Spinner from "../common/Spinner";
import type { WeatherOverviewZone } from "../../types/risk";

export default function WeatherOverviewPanel() {
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

  if (loading) {
    return (
      <div className="rounded-card p-4" style={{ background: 'rgba(229, 233, 224, 0.45)', backdropFilter: 'blur(8px)', border: '1px solid rgba(255,255,255,0.18)' }}>
        <div className="flex items-center gap-2 text-[14px] text-gs-text-secondary"><Spinner /> Loading weather...</div>
      </div>
    );
  }

  if (!forecasts.length) return null;

  return (
    <div className="rounded-card p-4" style={{ background: 'rgba(229, 233, 224, 0.45)', backdropFilter: 'blur(8px)', border: '1px solid rgba(255,255,255,0.18)' }}>
      <h3 className="text-[15px] font-bold text-gs-text mb-1">Region Weather Overview</h3>
      <p className="text-[12px] text-gs-text-secondary mb-3">{forecasts.length} zones monitored</p>

      {/* Alert badges */}
      <div className="flex gap-2 mb-3">
        {extremeCount > 0 && (
          <span className="px-2 py-1 rounded-full text-[11px] font-bold text-white" style={{ background: '#ba1a1a' }}>
            {extremeCount} EXTREME
          </span>
        )}
        {highCount > 0 && (
          <span className="px-2 py-1 rounded-full text-[11px] font-bold text-white" style={{ background: '#ea580c' }}>
            {highCount} HIGH
          </span>
        )}
      </div>

      {/* Weather cards */}
      <div className="space-y-2 max-h-72 overflow-y-auto">
        {forecasts.map((f) => (
          <div key={f.zone_id} className="rounded-lg p-3" style={{ background: 'rgba(255,255,255,0.35)', borderLeft: `3px solid ${f.risk_color}` }}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[13px] font-semibold text-gs-text">{f.name}</span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold text-white" style={{ background: f.risk_color }}>
                {f.risk_level}
              </span>
            </div>
            <div className="text-[11px] text-gs-text-secondary mb-1">{f.message}</div>
            <div className="grid grid-cols-3 gap-2 text-[11px]">
              <div>
                <span className="text-gs-text-secondary">Rain 24h</span>
                <div className="font-medium text-gs-text">{fmtMmOpt(f.rainfall_24h)}</div>
              </div>
              <div>
                <span className="text-gs-text-secondary">Soil</span>
                <div className="font-medium text-gs-text">{fmtPctOpt(f.soil_moisture)}</div>
              </div>
              <div>
                <span className="text-gs-text-secondary">Risk</span>
                <div className="font-bold text-gs-text">{fmtPctOpt(f.risk_score)}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

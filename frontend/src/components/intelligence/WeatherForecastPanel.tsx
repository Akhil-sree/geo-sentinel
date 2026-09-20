import { useEffect, useState } from "react";
import { getWeatherForecast } from "../../api/risk";
import { useUIStore } from "../../store/uiStore";
import { fmtPctOpt, fmtMmOpt } from "../../lib/format";
import Spinner from "../common/Spinner";
import type { WeatherForecast as WeatherForecastType } from "../../types/risk";

export default function WeatherForecastPanel() {
  const simTime = useUIStore((s) => s.simTime);
  const selectedZoneId = useUIStore((s) => s.selectedZoneId);
  const [forecast, setForecast] = useState<WeatherForecastType | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selectedZoneId) { setForecast(null); return; }
    setLoading(true);
    getWeatherForecast(selectedZoneId, simTime)
      .then(setForecast)
      .catch(() => setForecast(null))
      .finally(() => setLoading(false));
  }, [selectedZoneId, simTime]);

  if (!selectedZoneId) return null;

  if (loading) {
    return (
      <div className="rounded-card p-4" style={{ background: 'rgba(229, 233, 224, 0.45)', backdropFilter: 'blur(8px)', border: '1px solid rgba(255,255,255,0.18)' }}>
        <div className="flex items-center gap-2 text-[14px] text-gs-text-secondary"><Spinner /> Loading forecast...</div>
      </div>
    );
  }

  if (!forecast) return null;

  return (
    <div className="rounded-card p-4" style={{ background: 'rgba(229, 233, 224, 0.45)', backdropFilter: 'blur(8px)', border: '1px solid rgba(255,255,255,0.18)' }}>
      <h3 className="text-[15px] font-bold text-gs-text mb-1">Weather-Linked Risk Forecast</h3>
      <p className="text-[12px] text-gs-text-secondary mb-3">{forecast.name} — 72h projection</p>

      {/* Verdict banner */}
      <div className="rounded-lg p-3 mb-3 text-center" style={{ background: forecast.verdict_color + '18', border: `1px solid ${forecast.verdict_color}40` }}>
        <div className="text-[14px] font-bold" style={{ color: forecast.verdict_color }}>{forecast.verdict}</div>
        <div className="text-[11px] text-gs-text-secondary mt-1">Current risk: {fmtPctOpt(forecast.current_risk)}</div>
      </div>

      {/* Forecast timeline */}
      <div className="space-y-2">
        {forecast.forecasts.map((fc) => (
          <div key={fc.hours_ahead} className="rounded-lg p-3" style={{ background: 'rgba(255,255,255,0.35)' }}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[13px] font-semibold text-gs-text">+{fc.hours_ahead}h</span>
              <span className="px-2 py-0.5 rounded-full text-[11px] font-bold text-white" style={{ background: fc.rainfall_color }}>
                {fc.rainfall_intensity}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[12px]">
              <div className="flex justify-between">
                <span className="text-gs-text-secondary">Rainfall 24h</span>
                <span className="font-medium text-gs-text">{fmtMmOpt(fc.projected_rainfall_24h)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gs-text-secondary">Rainfall 72h</span>
                <span className="font-medium text-gs-text">{fmtMmOpt(fc.projected_rainfall_72h)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gs-text-secondary">Soil Moisture</span>
                <span className="font-medium text-gs-text">{fmtPctOpt(fc.projected_soil_moisture)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gs-text-secondary">Risk Score</span>
                <span className="font-bold" style={{ color: fc.slope_state_color }}>{fmtPctOpt(fc.projected_risk)}</span>
              </div>
            </div>
            <div className="flex items-center gap-2 mt-2">
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold text-white" style={{ background: fc.slope_state_color }}>
                {fc.slope_state_label}
              </span>
              {fc.escalated && <span className="px-2 py-0.5 rounded-full text-[10px] font-bold text-white bg-red-700">Escalated</span>}
            </div>
          </div>
        ))}
      </div>

      <p className="text-[10px] text-gs-text-secondary/60 mt-3 italic">{forecast.confidence_note}</p>
    </div>
  );
}

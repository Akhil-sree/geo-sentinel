import { useEffect, useState } from "react";
import { getWeatherForecast } from "../../api/risk";
import { useUIStore } from "../../store/uiStore";
import type { ForecastResult } from "../../api/risk";
import { t } from "../../lib/i18n";

export default function WeatherForecast({ zoneId }: { zoneId: string }) {
  const [forecast, setForecast] = useState<ForecastResult | null>(null);
  const [loading, setLoading] = useState(false);
  const simTime = useUIStore((s) => s.simTime);

  useEffect(() => {
    setLoading(true);
    getWeatherForecast(zoneId, simTime)
      .then(setForecast)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [zoneId, simTime]);

  if (loading) {
    return (
      <div className="rounded-lg border border-[#d9e2d9] bg-white p-3 shadow-sm">
        <div className="flex items-center gap-2">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-[#04442f] border-t-transparent" />
          <span className="text-[10px] text-[#707973]">Loading forecast...</span>
        </div>
      </div>
    );
  }

  if (!forecast) return null;

  return (
    <div className="overflow-hidden rounded-lg border border-[#d9e2d9] bg-white shadow-sm">
      {/* Header */}
      <div className="border-b border-[#e4e3db] bg-[#f8f7f3] px-3 py-2">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wide text-[#1b1c17]">
              {t("weatherForecast")}
            </p>
            <p className="text-[8px] text-[#707973]">{forecast.name}</p>
          </div>
          <span className="rounded bg-[#04442f]/10 px-1.5 py-0.5 text-[7px] font-bold text-[#04442f]">
            72H PROJECTION
          </span>
        </div>
      </div>

      {/* Verdict banner */}
      <div className="px-3 pt-2 pb-1">
        <div
          className="rounded-lg border p-2"
          style={{ borderColor: forecast.verdict_color + "40", backgroundColor: forecast.verdict_color + "08" }}
        >
          <div className="flex items-center gap-2">
            <span className="text-lg" style={{ color: forecast.verdict_color }}>
              {forecast.verdict_color === "#ba1a1a" ? "\u26A0" : forecast.verdict_color === "#245c45" ? "\u2713" : "\u25B2"}
            </span>
            <div>
              <p className="text-[10px] font-bold" style={{ color: forecast.verdict_color }}>
                {forecast.verdict}
              </p>
              <p className="text-[7px] text-[#707973]">{forecast.confidence_note}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Forecast cards */}
      <div className="grid grid-cols-3 gap-1.5 px-3 py-2">
        {forecast.forecasts.map((f) => (
          <div
            key={f.hours_ahead}
            className="rounded border p-2 text-center"
            style={{ borderColor: f.slope_state_color + "30" }}
          >
            <p className="text-[8px] font-bold text-[#707973]">+{f.hours_ahead}h</p>

            {/* Rainfall */}
            <div className="my-1">
              <span className="text-[7px] font-bold" style={{ color: f.rainfall_color }}>
                {f.rainfall_intensity}
              </span>
              <p className="text-[10px] font-bold text-[#1b1c17]">
                {f.projected_rainfall_24h.toFixed(0)}mm
              </p>
            </div>

            {/* Risk */}
            <div className="rounded py-0.5" style={{ backgroundColor: f.slope_state_color + "15" }}>
              <span className="text-[9px] font-bold" style={{ color: f.slope_state_color }}>
                {(f.projected_risk * 100).toFixed(0)}%
              </span>
            </div>

            {/* State */}
            <div className="mt-1 flex items-center justify-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: f.slope_state_color }} />
              <span className="text-[7px] font-bold" style={{ color: f.slope_state_color }}>
                {f.slope_state_label}
              </span>
            </div>

            {f.escalated && (
              <span className="mt-0.5 inline-block rounded bg-[#ba1a1a]/10 px-1 text-[6px] font-bold text-[#ba1a1a]">
                ESC
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Current vs projected comparison */}
      <div className="border-t border-[#e4e3db] px-3 py-2">
        <p className="mb-1 text-[8px] font-bold uppercase tracking-wider text-[#707973]">
          Risk Progression
        </p>
        <div className="flex items-center gap-1">
          <div className="flex-1 rounded bg-[#f0eee6] p-1.5 text-center">
            <p className="text-[7px] text-[#707973]">NOW</p>
            <p className="text-[11px] font-bold text-[#04442f]">{(forecast.current_risk * 100).toFixed(0)}%</p>
          </div>
          <svg width="16" height="10" viewBox="0 0 16 10" className="text-[#707973]">
            <path d="M0 5h14M12 2l3 3-3 3" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          {forecast.forecasts.length >= 3 ? (
            <>
              <div className="flex-1 rounded p-1.5 text-center" style={{ backgroundColor: (forecast.forecasts[2]?.slope_state_color || "#707973") + "10" }}>
                <p className="text-[7px] text-[#707973]">+72H</p>
                <p className="text-[11px] font-bold" style={{ color: forecast.forecasts[2]?.slope_state_color }}>
                  {((forecast.forecasts[2]?.projected_risk ?? 0) * 100).toFixed(0)}%
                </p>
              </div>
              <div className="text-center">
                <p className="text-[8px] font-bold" style={{
                  color: (forecast.forecasts[2]?.projected_risk ?? 0) > forecast.current_risk ? "#ba1a1a" : "#245c45"
                }}>
                  {(forecast.forecasts[2]?.projected_risk ?? 0) > forecast.current_risk ? "+" : ""}
                  {(((forecast.forecasts[2]?.projected_risk ?? 0) - forecast.current_risk) * 100).toFixed(1)}%
                </p>
              </div>
            </>
          ) : (
            <div className="flex-1 rounded bg-[#f0eee6] p-1.5 text-center">
              <p className="text-[7px] text-[#707973]">+72H</p>
              <p className="text-[11px] font-bold text-[#707973]">—</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

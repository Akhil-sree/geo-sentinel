import { useEffect, useState } from "react";
import { getWeatherOverview, type WeatherOverviewItem } from "../api/dashboard";
import { useUIStore } from "../store/uiStore";
import { t } from "../lib/i18n";

const RAINFALL_BAR = (mm: number) => {
  const pct = Math.min((mm / 80) * 100, 100);
  const color = mm > 50 ? "#ba1a1a" : mm > 25 ? "#ea580c" : mm > 10 ? "#d97706" : "#245c45";
  return { pct, color };
};

export default function WeatherForecastPage() {
  const [forecasts, setForecasts] = useState<WeatherOverviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [extremeCount, setExtremeCount] = useState(0);
  const [highCount, setHighCount] = useState(0);
  const selectZone = useUIStore((s) => s.selectZone);

  useEffect(() => {
    getWeatherOverview(24)
      .then((r) => {
        setForecasts(r.forecasts);
        setExtremeCount(r.extreme_count);
        setHighCount(r.high_count);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center bg-[#f0eee6]">
        <div className="text-center">
          <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-[#2563eb] border-t-transparent" />
          <p className="text-[11px] text-[#707973]">Loading weather forecast...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col overflow-y-auto bg-[#f0eee6]">
      {/* Header */}
      <div className="border-b border-[#2563eb]/20 bg-gradient-to-r from-[#2563eb] to-[#1d4ed8] px-5 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/20 text-white">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M10 2v2M10 16v2M4.93 4.93l1.41 1.41M13.66 13.66l1.41 1.41M2 10h2M16 10h2M4.93 15.07l1.41-1.41M13.66 6.34l1.41-1.41" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
                <circle cx="10" cy="10" r="3" stroke="white" strokeWidth="1.5" fill="none"/>
              </svg>
            </span>
            <div>
              <h1 className="text-lg font-bold text-white">{t("weatherForecast")}</h1>
              <p className="text-[10px] text-white/70">
                72-hour rainfall and risk-linked weather forecast
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {extremeCount > 0 && (
              <div className="rounded-lg bg-[#ba1a1a] px-3 py-1.5 text-center">
                <p className="text-xl font-bold text-white">{extremeCount}</p>
                <p className="text-[8px] font-bold text-white/80">EXTREME</p>
              </div>
            )}
            {highCount > 0 && (
              <div className="rounded-lg bg-[#ea580c] px-3 py-1.5 text-center">
                <p className="text-xl font-bold text-white">{highCount}</p>
                <p className="text-[8px] font-bold text-white/80">HIGH RISK</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Forecast cards */}
      <div className="space-y-2 px-5 py-3">
        {forecasts.map((f) => {
          const bar24 = RAINFALL_BAR(f.rainfall_24h);
          const bar72 = RAINFALL_BAR(f.rainfall_72h);
          return (
            <div
              key={f.zone_id}
              className="overflow-hidden rounded-lg border border-[#d9e2d9] bg-white shadow-sm transition hover:shadow-md"
            >
              <div className="flex items-stretch">
                {/* Risk level indicator */}
                <div
                  className="w-1.5 shrink-0"
                  style={{ backgroundColor: f.risk_color }}
                />

                <div className="flex-1 p-3">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      {/* Zone name + risk level */}
                      <div className="flex items-center gap-2">
                        <h3 className="text-[11px] font-bold text-[#1b1c17]">{f.name}</h3>
                        <span
                          className="rounded-full px-2 py-0.5 text-[8px] font-bold"
                          style={{ backgroundColor: f.risk_color + "15", color: f.risk_color }}
                        >
                          {f.risk_level}
                        </span>
                        {f.escalated && (
                          <span className="rounded bg-[#ba1a1a]/10 px-1.5 py-0.5 text-[7px] font-bold text-[#ba1a1a]">
                            ESCALATED
                          </span>
                        )}
                      </div>

                      <p className="mt-0.5 text-[9px] text-[#707973]">{f.district}</p>

                      {/* Rainfall bars */}
                      <div className="mt-2 space-y-1.5">
                        <div>
                          <div className="flex items-center justify-between text-[8px]">
                            <span className="text-[#707973]">{t("next24h")}</span>
                            <span className="font-bold" style={{ color: bar24.color }}>
                              {f.rainfall_24h.toFixed(1)} mm
                            </span>
                          </div>
                          <div className="mt-0.5 h-1.5 w-full rounded-full bg-[#e4e3db]">
                            <div
                              className="h-1.5 rounded-full transition-all duration-500"
                              style={{ width: `${bar24.pct}%`, backgroundColor: bar24.color }}
                            />
                          </div>
                        </div>
                        <div>
                          <div className="flex items-center justify-between text-[8px]">
                            <span className="text-[#707973]">{t("next72h")} cumulative</span>
                            <span className="font-bold" style={{ color: bar72.color }}>
                              {f.rainfall_72h.toFixed(1)} mm
                            </span>
                          </div>
                          <div className="mt-0.5 h-1.5 w-full rounded-full bg-[#e4e3db]">
                            <div
                              className="h-1.5 rounded-full transition-all duration-500"
                              style={{ width: `${bar72.pct}%`, backgroundColor: bar72.color }}
                            />
                          </div>
                        </div>
                      </div>

                      {/* Soil moisture + risk */}
                      <div className="mt-2 flex items-center gap-3 text-[8px] text-[#707973]">
                        <span>
                          {t("soilMoisture")}:{" "}
                          <span className="font-bold text-[#1b1c17]">
                            {(f.soil_moisture * 100).toFixed(0)}%
                          </span>
                        </span>
                        <span>
                          Risk:{" "}
                          <span className="font-bold" style={{ color: f.risk_color }}>
                            {(f.risk_score * 100).toFixed(0)}%
                          </span>
                        </span>
                        <span className="font-semibold" style={{ color: f.risk_color }}>
                          {f.message}
                        </span>
                      </div>
                    </div>

                    {/* Zone button */}
                    <button
                      onClick={() => selectZone(f.zone_id)}
                      className="ml-3 shrink-0 rounded border border-[#d9e2d9] px-2 py-1 text-[8px] font-bold text-[#04442f] transition hover:bg-[#04442f] hover:text-white"
                    >
                      Details
                    </button>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Disclaimer */}
      <div className="mx-5 mb-5 rounded-lg border border-[#d97706]/20 bg-[#d97706]/5 px-3 py-2">
        <p className="text-[8px] text-[#92400e]">
          Weather data is from IMD mock feeds. Forecasts are projections based on current rainfall
          patterns, not validated meteorological predictions. Always cross-reference with official
          IMD bulletins.
        </p>
      </div>
    </div>
  );
}

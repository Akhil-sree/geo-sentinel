import RainfallChart from "./RainfallChart";
import DynamicRiskChart from "./DynamicRiskChart";
import RiskTrajectoryChart from "./RiskTrajectoryChart";
import SlopeHealthTimeline from "./SlopeHealthTimeline";
import EventInventory from "./EventInventory";
import { useState } from "react";
import type { ZoneRisk } from "../../types/risk";

const soilLabel = (sm: number) =>
  sm > 0.45 ? "Saturated" : sm > 0.3 ? "Moist" : "Normal";

function TooltipIcon({ text }: { text: string }) {
  const [show, setShow] = useState(false);
  return (
    <span className="relative inline-flex ml-1">
      <button
        type="button"
        className="text-[13px] text-gs-text-secondary/60 hover:text-gs-text-secondary transition-colors"
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        onClick={() => setShow(!show)}
      >
        ⓘ
      </button>
      {show && (
        <span className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-52 rounded-lg px-3 py-2 text-[13px] leading-relaxed text-gs-text shadow-lg" style={{
          background: 'rgba(6, 18, 14, 0.85)',
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          border: '1px solid rgba(255, 255, 255, 0.10)',
          color: 'white',
        }}>
          {text}
        </span>
      )}
    </span>
  );
}

interface ZonePanelProps {
  risk: ZoneRisk;
  zoneId: string;
}

export function ZonePanel({ risk, zoneId }: ZonePanelProps) {
  return (
    <div className="space-y-4">

      {/* ── Key Risk Factors ── */}
      <div className="rounded-card p-4" style={{
        background: 'rgba(255, 255, 255, 0.55)',
        backdropFilter: 'blur(4px)',
        WebkitBackdropFilter: 'blur(4px)',
        border: '1px solid rgba(255, 255, 255, 0.30)',
        boxShadow: '0 2px 10px rgba(15, 35, 27, 0.04)',
      }}>
        <h3 className="text-[17px] font-semibold text-gs-text mb-3">
          KEY RISK FACTORS
        </h3>

        <div className="grid grid-cols-2 gap-3">
          <div className="text-center p-3 bg-gs-surface-soft rounded-card">
            <div className="flex items-center justify-center gap-1 mb-1">
              <p className="text-[14px] font-medium text-gs-text-secondary">
                Susceptibility
              </p>
              <TooltipIcon text="Static terrain-based risk from slope angle, elevation, geology, and land cover. Does not change with weather." />
            </div>
            <p className="text-[22px] font-bold text-gs-text">
              {Math.round(risk.static_score * 100)}%
            </p>
          </div>

          <div className="text-center p-3 bg-gs-surface-soft rounded-card">
            <div className="flex items-center justify-center gap-1 mb-1">
              <p className="text-[14px] font-medium text-gs-text-secondary">
                Recent risk
              </p>
              <TooltipIcon text="Dynamic event-driven risk from recent rainfall, soil moisture, and satellite-detected ground movement." />
            </div>
            <p className="text-[22px] font-bold text-gs-text">
              {Math.round(risk.dynamic_score * 100)}%
            </p>
          </div>

          <div className="text-center p-3 bg-gs-surface-soft rounded-card">
            <p className="text-[14px] font-medium text-gs-text-secondary mb-1">
              72h rainfall
            </p>
            <p className="text-[22px] font-bold text-gs-text">
              {risk.rainfall_72h.toFixed(0)} mm
            </p>
          </div>

          <div className="text-center p-3 bg-gs-surface-soft rounded-card">
            <p className="text-[14px] font-medium text-gs-text-secondary mb-1">
              Soil moisture
            </p>
            <p className="text-[22px] font-bold text-gs-text">
              {soilLabel(risk.soil_moisture)}
            </p>
          </div>
        </div>
      </div>

      {/* ── Charts ── */}
      <div className="grid grid-cols-2 gap-3">
        <div className="overflow-hidden rounded-card p-3" style={{
          background: 'rgba(255, 255, 255, 0.50)',
          backdropFilter: 'blur(4px)',
          WebkitBackdropFilter: 'blur(4px)',
          border: '1px solid rgba(255, 255, 255, 0.25)',
          boxShadow: '0 1px 6px rgba(15, 35, 27, 0.03)',
        }}>
          <p className="mb-2 text-[15px] font-medium text-gs-text">
            Rainfall (96h)
          </p>
          <div className="h-40 w-full">
            <RainfallChart zoneId={zoneId} />
          </div>
        </div>

        <div className="overflow-hidden rounded-card p-3" style={{
          background: 'rgba(255, 255, 255, 0.50)',
          backdropFilter: 'blur(4px)',
          WebkitBackdropFilter: 'blur(4px)',
          border: '1px solid rgba(255, 255, 255, 0.25)',
          boxShadow: '0 1px 6px rgba(15, 35, 27, 0.03)',
        }}>
          <p className="mb-2 text-[15px] font-medium text-gs-text">
            Risk over time
          </p>
          <div className="h-40 w-full">
            <DynamicRiskChart zoneId={zoneId} />
          </div>
        </div>
      </div>

      {/* Risk Trajectory */}
      <div className="overflow-hidden rounded-card p-3" style={{
        background: 'rgba(255, 255, 255, 0.50)',
        backdropFilter: 'blur(4px)',
        WebkitBackdropFilter: 'blur(4px)',
        border: '1px solid rgba(255, 255, 255, 0.25)',
        boxShadow: '0 1px 6px rgba(15, 35, 27, 0.03)',
      }}>
        <RiskTrajectoryChart zoneId={zoneId} />
      </div>

      {/* Slope Health */}
      <SlopeHealthTimeline zoneId={zoneId} />

      {/* ── Recent Events ── */}
      <div className="overflow-hidden rounded-card p-3" style={{
        background: 'rgba(255, 255, 255, 0.50)',
        backdropFilter: 'blur(4px)',
        WebkitBackdropFilter: 'blur(4px)',
        border: '1px solid rgba(255, 255, 255, 0.25)',
        boxShadow: '0 1px 6px rgba(15, 35, 27, 0.03)',
      }}>
        <p className="mb-2 text-[15px] font-medium text-gs-text">
          Recent events
        </p>
        <EventInventory />
      </div>

    </div>
  );
}

import RainfallChart from "./RainfallChart";
import DynamicRiskChart from "./DynamicRiskChart";
import RiskTrajectoryChart from "./RiskTrajectoryChart";
import SlopeHealthTimeline from "./SlopeHealthTimeline";
import SlopeStatePlayback from "./SlopeStatePlayback";
import CellGridDashboard from "./CellGridDashboard";
import EventInventory from "./EventInventory";
import AlertSection from "./AlertSection";
import TerrainFacts from "./TerrainFacts";
import SlopeStateBadge from "../common/SlopeStateBadge";
import type { ZoneRisk } from "../../types/risk";

const soilLabel = (sm: number) =>
  sm > 0.45 ? "SATURATED" : sm > 0.3 ? "MOIST" : "NORMAL";

interface ZonePanelProps {
  risk: ZoneRisk;
  zoneId: string;
}

export function ZonePanel({ risk, zoneId }: ZonePanelProps) {
  const isFlagship = zoneId === "Z1";

  return (
    <div className="space-y-2.5 bg-[#f0eee6] p-3">

      {/* =====================================================
          AREA OVERVIEW
      ====================================================== */}
      <div className="rounded-lg border border-[#d9e2d9] bg-white p-3 shadow-sm">

        <div className="mb-1.5 flex items-center justify-between">
          <h3 className="font-headline text-sm font-bold uppercase tracking-wide">
            Area Overview
          </h3>
          <span className="text-[10px] text-[#707973]">Meghalaya</span>
        </div>

        <p className="mb-2 text-[10px] text-[#404943]">
          {risk.name}, {risk.district}
        </p>

        <div className="grid grid-cols-3 gap-2 border-b border-[#e4e3db] pb-2.5">
          {/* Slope State */}
          <div>
            <p className="text-[8px] font-bold tracking-wider text-[#707973]">SLOPE STATE</p>
            {risk.slope_state ? (
              <div className="mt-0.5">
                <SlopeStateBadge state={risk.slope_state} label={risk.slope_state_label} size="md" stressScore={risk.slope_stress_score} />
              </div>
            ) : (
              <span className="mt-0.5 inline-block rounded-full bg-[#e4e3db] px-2 py-0.5 text-[10px] text-[#707973]">
                Analyzing...
              </span>
            )}
          </div>

          {/* Risk Score */}
          <div>
            <p className="text-[8px] font-bold tracking-wider text-[#707973]">RISK SCORE</p>
            <p className="text-2xl font-bold text-[#04442f]">
              {risk.risk_score.toFixed(2)}
              {risk.escalated && (
                <span className="ml-1 rounded bg-[#ba1a1a]/10 px-1 text-[9px] font-bold text-[#ba1a1a]">ESC</span>
              )}
            </p>
          </div>

          {/* Model Confidence */}
          <div>
            <p className="text-[8px] font-bold tracking-wider text-[#707973]">CONFIDENCE</p>
            <p className="text-xl font-bold text-[#04442f]">{Math.round(risk.confidence * 100)}%</p>
          </div>
        </div>

        <p className="mt-2 text-[9px] leading-relaxed text-[#404943]">{risk.summary}</p>
      </div>

      {/* =====================================================
          KEY INDICATORS
      ====================================================== */}
      <div className="grid grid-cols-2 gap-2">
        <Indicator
          title="RF STATIC"
          value={risk.static_score.toFixed(2)}
          tone="mid"
          sub="Terrain susceptibility (Random Forest)"
        />
        <Indicator
          title="MAMBA DYNAMIC"
          value={risk.dynamic_score.toFixed(2)}
          tone={risk.dynamic_score > 0.5 ? "high" : "mid"}
          sub="Temporal trajectory"
          alert={risk.escalated}
        />
        <Indicator
          title="24H RAINFALL"
          value={`${risk.rainfall_24h.toFixed(1)} mm`}
          tone={risk.rainfall_24h > 50 ? "high" : "mid"}
          sub={`72h: ${risk.rainfall_72h.toFixed(1)} mm`}
        />
        <Indicator
          title="SOIL MOISTURE"
          value={soilLabel(risk.soil_moisture)}
          tone={risk.soil_moisture > 0.45 ? "high" : "mid"}
          sub="Regional proxy"
        />
      </div>

      {/* =====================================================
          CHARTS
      ====================================================== */}
      <div className="grid grid-cols-2 gap-2">
        <div className="overflow-hidden rounded-lg border border-[#d9e2d9] bg-white p-2 shadow-sm">
          <p className="mb-1 text-[9px] font-bold uppercase tracking-wide text-[#1b1c17]">Rainfall (96h)</p>
          <div className="h-28 w-full"><RainfallChart zoneId={zoneId} /></div>
        </div>
        <div className="overflow-hidden rounded-lg border border-[#d9e2d9] bg-white p-2 shadow-sm">
          <p className="mb-1 text-[9px] font-bold uppercase tracking-wide text-[#1b1c17]">Risk Over Time</p>
          <div className="h-28 w-full"><DynamicRiskChart zoneId={zoneId} /></div>
        </div>
      </div>

      {/* Risk Trajectory — full width */}
      <div className="overflow-hidden rounded-lg border border-[#d9e2d9] bg-white p-2 shadow-sm">
        <RiskTrajectoryChart zoneId={zoneId} />
      </div>

      {/* =====================================================
          SLOPE STATE ANALYSIS
      ====================================================== */}
      <SectionHeader
        icon={
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M1 9L4 4L7 6L11 2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        }
        title="Slope State Analysis"
        subtitle="How slope health changes over time"
      />
      <SlopeHealthTimeline zoneId={zoneId} />
      <SlopeStatePlayback zoneId={zoneId} />

      {/* =====================================================
          PER-CELL TERRAIN INTELLIGENCE (flagship only)
      ====================================================== */}
      {isFlagship && (
        <>
          <SectionHeader
            icon={
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <rect x="1" y="1" width="3" height="3" rx="0.5" stroke="currentColor" strokeWidth="1"/>
                <rect x="5" y="1" width="3" height="3" rx="0.5" stroke="currentColor" strokeWidth="1"/>
                <rect x="9" y="1" width="2" height="3" rx="0.5" stroke="currentColor" strokeWidth="1"/>
                <rect x="1" y="5" width="3" height="3" rx="0.5" stroke="currentColor" strokeWidth="1"/>
                <rect x="5" y="5" width="3" height="3" rx="0.5" fill="currentColor" opacity="0.3"/>
                <rect x="9" y="5" width="2" height="3" rx="0.5" stroke="currentColor" strokeWidth="1"/>
                <rect x="1" y="9" width="3" height="2" rx="0.5" stroke="currentColor" strokeWidth="1"/>
                <rect x="5" y="9" width="3" height="2" rx="0.5" stroke="currentColor" strokeWidth="1"/>
                <rect x="9" y="9" width="2" height="2" rx="0.5" stroke="currentColor" strokeWidth="1"/>
              </svg>
            }
            title="Deep-Dive: Per-Cell Terrain Intelligence"
            subtitle="Flagship zone — RF model runs on each 400m cell"
            highlight
          />
          <CellGridDashboard zoneId={zoneId} />
        </>
      )}

      {/* =====================================================
          DRIVERS + TERRAIN
      ====================================================== */}
      <SectionHeader
        icon={
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1"/>
            <path d="M6 3v3.5l2 1.5" stroke="currentColor" strokeWidth="1" strokeLinecap="round"/>
          </svg>
        }
        title="Risk Drivers & Terrain"
      />
      <div className="grid grid-cols-2 gap-2">
        <div className="overflow-hidden rounded-lg border border-[#d9e2d9] bg-white p-2 shadow-sm">
          <p className="mb-1.5 text-[9px] font-bold uppercase tracking-wide text-[#1b1c17]">Drivers</p>
          <ul className="space-y-1">
            {risk.drivers.map((d) => (
              <li key={d.factor} className="flex items-center gap-1.5 text-[8px]">
                <span className="w-20 shrink-0 truncate text-[#404943]">{d.factor}</span>
                <span className="h-1.5 flex-1 rounded-full bg-[#e4e3db]">
                  <span className="block h-1.5 rounded-full bg-[#04442f]" style={{ width: `${Math.min(100, Math.abs(d.impact) * 100)}%` }} />
                </span>
                <span className={`w-12 shrink-0 text-right font-bold ${d.impact > 0.6 ? "text-[#04442f]" : "text-[#d97706]"}`}>
                  {d.impact > 0.6 ? "High" : "Mod"}
                </span>
              </li>
            ))}
          </ul>
        </div>
        <div className="overflow-hidden rounded-lg border border-[#d9e2d9] bg-white p-2 shadow-sm">
          <p className="mb-1 text-[9px] font-bold uppercase tracking-wide text-[#1b1c17]">Terrain & Satellite</p>
          <TerrainFacts zoneId={zoneId} />
        </div>
      </div>

      {/* =====================================================
          RECENT EVENTS
      ====================================================== */}
      <div className="overflow-hidden rounded-lg border border-[#d9e2d9] bg-white p-2 shadow-sm">
        <p className="mb-1 text-[9px] font-bold uppercase tracking-wide text-[#1b1c17]">Recent Events</p>
        <EventInventory zoneId={zoneId} />
      </div>

      {/* =====================================================
          MODEL PROVENANCE
      ====================================================== */}
      <div className="rounded-lg border border-[#d9e2d9] bg-white p-2 shadow-sm">
        <p className="mb-0.5 text-[8px] font-bold uppercase tracking-wider text-[#707973]">Model Provenance</p>
        <span className="font-mono text-[8px] text-[#707973]">
          rf:{risk.model_versions.rf} · temporal:{risk.model_versions.mamba} · fusion:{risk.model_versions.fusion}
        </span>
        <p className="mt-1 text-[7px] text-[#92400e]">
          Severity boundaries &amp; escalation rules are calibration parameters, not validated constants.
        </p>
      </div>

      {/* =====================================================
          ALERT DISPATCH
      ====================================================== */}
      <div className="overflow-hidden rounded-lg border border-[#d9e2d9] bg-white p-2 shadow-sm">
        <p className="mb-1 text-[9px] font-bold uppercase tracking-wide text-[#1b1c17]">Alert Dispatch</p>
        <AlertSection risk={risk} />
      </div>

    </div>
  );
}


/* =============================================================
   SECTION HEADER
============================================================= */

function SectionHeader({ icon, title, subtitle, highlight }: {
  icon: React.ReactNode;
  title: string;
  subtitle?: string;
  highlight?: boolean;
}) {
  return (
    <div className={`flex items-center gap-2 rounded-lg px-2.5 py-1.5 ${
      highlight
        ? "border border-[#04442f]/20 bg-[#04442f]/5"
        : "border border-[#d9e2d9] bg-white"
    }`}>
      <span className={highlight ? "text-[#04442f]" : "text-[#707973]"}>{icon}</span>
      <div>
        <p className={`text-[10px] font-bold uppercase tracking-wide ${highlight ? "text-[#04442f]" : "text-[#1b1c17]"}`}>
          {title}
        </p>
        {subtitle && <p className="text-[7px] text-[#707973]">{subtitle}</p>}
      </div>
    </div>
  );
}


/* =============================================================
   INDICATOR COMPONENT
============================================================= */

interface IndicatorProps {
  title: string;
  value: string;
  tone: "high" | "mid" | "low";
  sub: string;
  alert?: boolean;
}

const Indicator = ({ title, value, tone, sub, alert }: IndicatorProps) => (
  <div className="overflow-hidden rounded-lg border border-[#d9e2d9] bg-white p-2 shadow-sm">
    <div className="flex justify-between text-[8px] font-bold tracking-wide text-[#707973]">
      <span>{title}</span>
      {alert && <span className="text-[#ba1a1a]" title="Escalation triggered">!</span>}
    </div>
    <p className={`mt-0.5 text-lg font-bold ${
      tone === "high" ? "text-[#ba1a1a]" : tone === "mid" ? "text-[#d97706]" : "text-[#04442f]"
    }`}>
      {value}
    </p>
    <p className="text-[7px] leading-tight text-[#707973]">{sub}</p>
  </div>
);

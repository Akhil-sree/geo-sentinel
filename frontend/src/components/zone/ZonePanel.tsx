import RainfallChart from "./RainfallChart";
import DynamicRiskChart from "./DynamicRiskChart";
import EventInventory from "./EventInventory";
import AlertSection from "./AlertSection";
import TerrainFacts from "./TerrainFacts";
import type { ZoneRisk } from "../../types/risk";

const soilLabel = (sm: number) =>
  sm > 0.45 ? "SATURATED" : sm > 0.3 ? "MOIST" : "NORMAL";

interface ZonePanelProps {
  risk: ZoneRisk;
  zoneId: string;
}

export function ZonePanel({ risk, zoneId }: ZonePanelProps) {
  return (
    <div className="space-y-2 bg-[#f0eee6] p-3">

      {/* =====================================================
          AREA OVERVIEW
      ====================================================== */}
      <div className="rounded bg-white p-3 shadow-sm">

        <div className="mb-1 flex items-center justify-between">

          <h3 className="font-headline text-sm font-bold uppercase tracking-wide">
            Area Overview
          </h3>

          <span className="text-[10px] text-[#707973]">
            📍 Meghalaya
          </span>

        </div>

        <p className="mb-2 text-[10px] text-[#404943]">
          📍 {risk.name}, {risk.district}
        </p>

        <div className="grid grid-cols-3 gap-2 border-b border-[#e4e3db] pb-2">

          {/* Overall Risk */}
          <div>

            <p className="text-[8px] font-bold tracking-wider text-[#707973]">
              OVERALL RISK
            </p>

            <span
              className={`mt-0.5 inline-block rounded-full px-2 py-0.5 text-[10px] font-bold text-white ${
                risk.severity === "VERY_HIGH" ||
                risk.severity === "HIGH"
                  ? "bg-[#ba1a1a]"
                  : risk.severity === "MODERATE"
                    ? "bg-[#d97706]"
                    : "bg-[#245c45]"
              }`}
            >
              ⚠ {risk.severity.replace("_", " ")}
            </span>

          </div>


          {/* Risk Score */}
          <div>

            <p className="text-[8px] font-bold tracking-wider text-[#707973]">
              RISK SCORE
            </p>

            <p className="text-2xl font-bold text-[#04442f]">
              {risk.risk_score.toFixed(2)}

              {risk.escalated && (
                <span className="ml-1 rounded bg-[#ba1a1a]/10 px-1 text-[9px] font-bold text-[#ba1a1a]">
                  ▲ ESC
                </span>
              )}
            </p>

          </div>


          {/* Model Confidence */}
          <div>

            <p className="text-[8px] font-bold tracking-wider text-[#707973]">
              MODEL CONFIDENCE
            </p>

            <p className="text-xl font-bold text-[#04442f]">
              {Math.round(risk.confidence * 100)}%
            </p>

          </div>

        </div>

        <p className="mt-1.5 text-[9px] leading-relaxed text-[#404943]">
          {risk.summary}
        </p>

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
          sub={`72h: ${risk.rainfall_72h.toFixed(1)} mm · 7d: ${risk.rainfall_7d.toFixed(1)} mm · slope: ${
            risk.rainfall_slope > 0 ? "+" : ""
          }${risk.rainfall_slope.toFixed(1)}`}
        />

        <Indicator
          title="SOIL MOISTURE"
          value={soilLabel(risk.soil_moisture)}
          tone={risk.soil_moisture > 0.45 ? "high" : "mid"}
          sub="Regional proxy — latency noted in freshness bar"
        />

      </div>


      {/* =====================================================
          CHARTS
      ====================================================== */}
      <div className="grid grid-cols-2 gap-2">

        {/* Rainfall */}
        <div className="overflow-hidden rounded bg-white p-2 shadow-sm">

          <p className="mb-1 text-[10px] font-bold text-[#1b1c17]">
            RAINFALL (LAST 96H)
          </p>

          <div className="h-32 w-full">
            <RainfallChart zoneId={zoneId} />
          </div>

        </div>


        {/* Dynamic Risk */}
        <div className="overflow-hidden rounded bg-white p-2 shadow-sm">

          <p className="mb-1 text-[10px] font-bold text-[#1b1c17]">
            RISK OVER SIM TIME
          </p>

          <div className="h-32 w-full">
            <DynamicRiskChart zoneId={zoneId} />
          </div>

        </div>

      </div>


      {/* =====================================================
          DRIVERS + TERRAIN
      ====================================================== */}
      <div className="grid grid-cols-2 gap-2">

        {/* Drivers */}
        <div className="overflow-hidden rounded bg-white p-2 shadow-sm">

          <p className="mb-1.5 text-[10px] font-bold text-[#1b1c17]">
            DRIVERS

            <span className="ml-1 text-[8px] font-normal text-[#707973]">
              (From Backend, Not Invented)
            </span>
          </p>

          <ul className="space-y-1">

            {risk.drivers.map((d) => (
              <li
                key={d.factor}
                className="flex items-center gap-1.5 text-[9px]"
              >

                <span className="w-24 shrink-0 truncate text-[#404943]">
                  {d.factor}
                </span>

                <span className="h-1.5 flex-1 rounded-full bg-[#e4e3db]">

                  <span
                    className="block h-1.5 rounded-full bg-[#04442f]"
                    style={{
                      width: `${Math.min(
                        100,
                        Math.abs(d.impact) * 100
                      )}%`,
                    }}
                  />

                </span>

                <span
                  className={`w-14 shrink-0 text-right font-bold ${
                    d.impact > 0.6
                      ? "text-[#04442f]"
                      : "text-[#d97706]"
                  }`}
                >
                  {d.impact > 0.6 ? "High" : "Moderate"}
                </span>

              </li>
            ))}

          </ul>

        </div>


        {/* Terrain */}
        <div className="overflow-hidden rounded bg-white p-2 shadow-sm">

          <p className="mb-1 text-[10px] font-bold text-[#1b1c17]">
            TERRAIN & SATELLITE
          </p>

          <TerrainFacts zoneId={zoneId} />

        </div>

      </div>


      {/* =====================================================
          RECENT EVENTS
      ====================================================== */}
      <div className="overflow-hidden rounded bg-white p-2 shadow-sm">

        <p className="mb-1 text-[10px] font-bold text-[#1b1c17]">
          RECENT EVENTS
        </p>

        <EventInventory zoneId={zoneId} />

      </div>


      {/* =====================================================
          MODEL PROVENANCE
      ====================================================== */}
      <div className="rounded bg-white p-2 text-[9px] text-[#707973] shadow-sm">

        <span className="font-mono">
          rf:{risk.model_versions.rf} · temporal:
          {risk.model_versions.mamba} · fusion:
          {risk.model_versions.fusion}
        </span>

        <p className="mt-1 text-[#92400e]">
          Severity boundaries &amp; escalation rules are
          calibration parameters, not validated constants.
        </p>

      </div>


      {/* =====================================================
          ALERT DISPATCH
      ====================================================== */}
      <div className="overflow-hidden rounded bg-white p-2 shadow-sm">

        <p className="mb-1 text-[10px] font-bold text-[#1b1c17]">
          ALERT DISPATCH
        </p>

        <AlertSection risk={risk} />

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

const Indicator = ({
  title,
  value,
  tone,
  sub,
  alert,
}: IndicatorProps) => (
  <div className="overflow-hidden rounded bg-white p-2 shadow-sm">

    <div className="flex justify-between text-[8px] font-bold tracking-wide text-[#707973]">

      <span>{title}</span>

      {alert && (
        <span
          className="text-[#ba1a1a]"
          title="Escalation triggered"
        >
          🔔
        </span>
      )}

    </div>

    <p
      className={`mt-0.5 text-lg font-bold ${
        tone === "high"
          ? "text-[#ba1a1a]"
          : tone === "mid"
            ? "text-[#d97706]"
            : "text-[#04442f]"
      }`}
    >
      {value}
    </p>

    <p className="text-[8px] leading-tight text-[#707973]">
      {sub}
    </p>

  </div>
);

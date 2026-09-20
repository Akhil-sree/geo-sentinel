import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import RiskMap from "../components/map/RiskMap";
import SimTimeline from "../components/timeline/SimTimeline";
import { ZonePanel } from "../components/zone/ZonePanel";
import ReportModal from "../components/reports/ReportModal";
import DataFreshnessBar from "../components/layout/DataFreshnessBar";
import AreaRiskPanel from "../components/area/AreaRiskPanel";
import GovernmentIntelligencePanel from "../components/intelligence/GovernmentIntelligencePanel";
import CriticalSlopeCard from "../components/intelligence/CriticalSlopeCard";
import WhyThisLocation from "../components/intelligence/WhyThisLocation";
import RainfallScenarioControl from "../components/intelligence/RainfallScenarioControl";
import EmergencyPrioritiesPanel from "../components/intelligence/EmergencyPrioritiesPanel";
import EmergencyTasksPanel from "../components/intelligence/EmergencyTasksPanel";
import SeveritySummaryPanel from "../components/intelligence/SeveritySummaryPanel";
import WeatherOverviewPanel from "../components/intelligence/WeatherOverviewPanel";
import WeatherForecastPanel from "../components/intelligence/WeatherForecastPanel";
import SoilMoistureDetail from "../components/intelligence/SoilMoistureDetail";
import CellRiskGrid from "../components/intelligence/CellRiskGrid";
import GsPointPanel from "../components/gs/GsPointPanel";
import RoadContext from "../components/gs/RoadContext";
import RoadConnectivityPanel from "../components/intelligence/RoadConnectivityPanel";
import RescueRoutePanel from "../components/intelligence/RescueRoutePanel";
import EvacuationRoutePanel from "../components/intelligence/EvacuationRoutePanel";
import ObservationIntelligencePanel from "../components/intelligence/ObservationIntelligencePanel";
import ResizableSidebar from "../components/common/ResizableSidebar";
import { getZones } from "../api/zones";
import { getRiskMap, getRiskIntensification } from "../api/risk";
import { useUIStore } from "../store/uiStore";
import { useSimClock } from "../hooks/useSimClock";
import { useI18n } from "../lib/i18n";
import type { IntensificationResult, SimulationResult } from "../types/risk";
import type { Zone } from "../api/zones";

const TAB_KEYS = ["zone", "intelligence", "scenario"] as const;
const TAB_LABELS = ["Location", "Intelligence", "Scenario"];

export default function CommandCenter() {
  const { zoneId } = useParams();
  const navigate = useNavigate();
  const simTime = useUIStore((s) => s.simTime);
  const selectZone = useUIStore((s) => s.selectZone);
  const { t } = useI18n();
  useSimClock();

  const [zones, setZones] = useState<Zone[]>([]);
  const [risks, setRisks] = useState<any[]>([]);
  const [reports, setReports] = useState<any[]>([]);
  const [reportOpen, setReportOpen] = useState(false);
  const [intensification, setIntensification] = useState<IntensificationResult[]>([]);
  const [simResults, setSimResults] = useState<SimulationResult[] | null>(null);
  const [simLabel, setSimLabel] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [sideTab, setSideTab] = useState<"zone" | "intelligence" | "scenario">("zone");

  useEffect(() => { getZones().then(setZones).catch(() => {}); }, []);
  useEffect(() => {
    import("../api/reports").then((m) => m.getReports().then(setReports).catch(() => {}));
  }, []);

  const loadRisks = useCallback(() => {
    setLoadError(null);
    getRiskMap(simTime).then((r) => {
      setRisks(r);
      const selected = useUIStore.getState().selectedZoneId;
      if (!selected && !zoneId) {
        const worst = r.reduce((a, b) => (b.risk_score > a.risk_score ? b : a), r[0]);
        if (worst) selectZone(worst.zone_id);
      }
    }).catch(() => setLoadError("Risk service unreachable — is the backend running on :8000?"));
    getRiskIntensification(simTime).then((r) => setIntensification(r.intensification)).catch(() => {});
  }, [simTime, zoneId, selectZone]);

  useEffect(() => { loadRisks(); }, [loadRisks]);

  useEffect(() => { if (zoneId) { selectZone(zoneId); } }, [zoneId, selectZone]);

  const selectedZoneId = useUIStore((s) => s.selectedZoneId);
  const selectedRisk = risks.find((r) => r.zone_id === selectedZoneId);
  const anyEscalated = risks.some((r) => r.escalated);
  const escalatedCount = risks.filter((r) => r.escalated).length;
  const stripUpdated = (() => {
    try {
      const iso = selectedRisk?.sim_time;
      const d = iso ? new Date(iso) : new Date();
      return d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }) + " IST";
    } catch {
      return "—";
    }
  })();

  const criticalCount = risks.filter((r) => r.slope_state === "CRITICAL").length;
  const degradingCount = risks.filter((r) => r.slope_state === "DEGRADING").length;

  useEffect(() => {
    if (selectedZoneId) setSideTab("zone");
  }, [selectedZoneId]);

  const handleSimResults = useCallback((results: SimulationResult[], label: string) => {
    setSimResults(results);
    setSimLabel(label);
    setSideTab("intelligence");
  }, []);

  const handleClearSim = useCallback(() => {
    setSimResults(null);
    setSimLabel(null);
  }, []);

  return (
    <div className="flex flex-1 flex-col overflow-hidden">

      {/* ── Advisory bar — compact institutional ── */}
      {anyEscalated && (
        <div className="flex items-center gap-3 px-4 py-2" role="alert" style={{
          background: 'linear-gradient(90deg, rgba(185,28,28,0.06) 0%, rgba(185,28,28,0.02) 100%)',
          borderBottom: '1px solid rgba(185,28,28,0.12)',
        }}>
          <span className="shrink-0 flex items-center gap-1.5">
            <span className="inline-block h-2 w-2 rounded-full" style={{ background: (criticalCount + degradingCount) > 0 ? '#B4232B' : '#D19217' }} />
            <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: '#7A4F08' }}>
              Active Advisory
            </span>
          </span>
          <span className="text-[12px] text-gs-text-secondary">
            <strong className="text-gs-text">{escalatedCount}</strong> location{escalatedCount === 1 ? "" : "s"} require attention
          </span>
          <button
            onClick={() => navigate("/alerts")}
            className="ml-auto shrink-0 text-[11px] font-semibold uppercase tracking-wide transition hover:opacity-80"
            style={{ color: '#075240' }}
          >
            View Alerts →
          </button>
        </div>
      )}

      {/* ── Service error banner ── */}
      {loadError && (
        <div className="mx-3 mt-2 flex items-center gap-3 rounded-lg px-4 py-3" style={{
          background: 'rgba(185, 26, 26, 0.92)',
          border: '1px solid rgba(255, 215, 200, 0.18)',
        }}>
          <span className="text-[13px] font-medium text-white">{loadError}</span>
          <button
            onClick={loadRisks}
            className="ml-auto shrink-0 rounded-full bg-white/25 px-3 py-1 text-[12px] font-semibold text-white transition hover:bg-white/35"
          >
            ↻ Retry
          </button>
        </div>
      )}

      {/* ── Main Content: Map + Intelligence Console ── */}
      <div className="relative flex flex-1 overflow-hidden">

        {/* Map Area — primary workspace */}
        <div className="relative flex-1">
          <RiskMap zones={zones} risks={risks}
            selectedId={selectedZoneId}
            reports={reports}
            intensification={intensification}
            simulationResults={simResults}
            simulationLabel={simLabel}
            onClearSimulation={handleClearSim}
            onSelect={(id) => useUIStore.getState().selectZone(id)} />
          {sideTab === "scenario" && <SimTimeline />}
        </div>

        {/* ── Intelligence Console (Right Panel) ── */}
        <ResizableSidebar>

          {/* Data Provenance Bar */}
          <DataFreshnessBar />

          {/* Panel Tabs — institutional tab bar */}
          <div className="flex gap-0 px-0 pt-0" style={{
            background: 'rgba(255,255,255,0.95)',
            borderBottom: '1px solid #E5E7EB',
          }}>
            {TAB_KEYS.map((key, i) => (
              <button
                key={key}
                onClick={() => setSideTab(key)}
                className={`relative flex-1 py-2.5 text-[11px] font-bold uppercase tracking-wider transition-colors ${
                  sideTab === key
                    ? "gs-tab-active text-gs-text"
                    : "text-gs-text-secondary hover:text-gs-text"
                }`}
                style={{
                  background: sideTab === key ? 'rgba(7,82,64,0.04)' : 'transparent',
                }}
              >
                {TAB_LABELS[i]}
              </button>
            ))}
          </div>

          {/* Panel Content (scrollable) */}
          <div className="flex-1 overflow-y-auto">

            {sideTab === "zone" && (
              <>
                {/* Report action */}
                <div className="flex items-center justify-between gap-2 px-4 pt-3 pb-2">
                  <p className="gs-label">Field Report</p>
                  <button
                    onClick={() => setReportOpen(true)}
                    className="rounded-lg bg-forest px-3 py-1.5 text-[12px] font-semibold text-white transition hover:bg-forest-dark active:scale-[0.98]"
                  >
                    + {t("btn.reportLandslide")}
                  </button>
                </div>

                {selectedRisk ? (
                  <div className="p-4 space-y-0">
                    {/* Location Intelligence Header */}
                    <AreaRiskPanel risk={selectedRisk} />

                    {/* GS Point Assessment */}
                    {(() => {
                      const z = zones.find((zz) => zz.id === selectedZoneId);
                      return z ? (
                        <>
                          <div className="gs-section-rule my-3" />
                          <GsPointPanel lat={z.lat} lng={z.lng} label={z.name} />
                          <div className="gs-section-rule my-3" />
                          <RoadContext lat={z.lat} lng={z.lng} />
                          <div className="gs-section-rule my-3" />
                          <RescueRoutePanel zones={zones} />
                        </>
                      ) : null;
                    })()}

                    {/* Evidence & Slope Assessment */}
                    <div className="gs-section-rule my-3" />
                    <CriticalSlopeCard />

                    {/* Why This Location */}
                    <div className="gs-section-rule my-3" />
                    <WhyThisLocation />

                    {/* Zone Details */}
                    <div className="gs-section-rule my-3" />
                    <ZonePanel risk={selectedRisk} zoneId={selectedRisk.zone_id} />

                    {/* Weather & Soil */}
                    <div className="gs-section-rule my-3" />
                    <WeatherForecastPanel />
                    <div className="gs-section-rule my-3" />
                    <SoilMoistureDetail />

                    {/* Per-Cell Grid */}
                    <div className="gs-section-rule my-3" />
                    <CellRiskGrid />
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center p-10 text-center">
                    <div className="mb-3 text-4xl text-gs-border opacity-40">◉</div>
                    <p className="text-[15px] font-medium text-gs-text-secondary">
                      {t("common.selectZone")}
                    </p>
                    <p className="mt-1.5 text-[13px] text-gs-text-secondary/60">
                      {t("common.clickPolygon")}
                    </p>
                  </div>
                )}
              </>
            )}

            {sideTab === "intelligence" && (
              <div className="p-4 space-y-0">
                <GovernmentIntelligencePanel />
                <div className="gs-section-rule my-3" />
                <SeveritySummaryPanel />
                <div className="gs-section-rule my-3" />
                <EmergencyPrioritiesPanel />
                <div className="gs-section-rule my-3" />
                <EmergencyTasksPanel />
                <div className="gs-section-rule my-3" />
                <WeatherOverviewPanel />
                <div className="gs-section-rule my-3" />
                <RoadConnectivityPanel />
                <div className="gs-section-rule my-3" />
                <ObservationIntelligencePanel />
                <div className="gs-section-rule my-3" />
                <EvacuationRoutePanel />
              </div>
            )}

            {sideTab === "scenario" && (
              <div className="p-4 space-y-4">
                <RainfallScenarioControl onResults={handleSimResults} onClear={handleClearSim} />
              </div>
            )}

          </div>
        </ResizableSidebar>

        <ReportModal open={reportOpen} onClose={() => setReportOpen(false)} />
      </div>

      {/* ── Bottom status bar — institutional ── */}
      <div className="gs-status-bar flex shrink-0 items-center gap-4 overflow-x-auto px-4 py-1.5" role="status" aria-label="Operational status">
        <span className="shrink-0">Last Update <strong className="tabular-nums text-gs-text">{stripUpdated}</strong></span>
        <span className="h-3 w-px shrink-0 bg-gs-border" aria-hidden />
        <span className="shrink-0"><strong className="tabular-nums text-gs-text">{zones.length}</strong> Monitored</span>
        <span className="h-3 w-px shrink-0 bg-gs-border" aria-hidden />
        <span className="shrink-0"><strong className="tabular-nums text-gs-text">{escalatedCount}</strong> Advisories</span>
        <span className="h-3 w-px shrink-0 bg-gs-border" aria-hidden />
        <span className="shrink-0">Road Network <strong className="text-gs-text">OSM</strong></span>
      </div>
    </div>
  );
}

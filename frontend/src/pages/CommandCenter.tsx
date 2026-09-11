import { useEffect, useState, useCallback } from "react";
import { useParams } from "react-router-dom";
import RiskMap from "../components/map/RiskMap";
import type { MapMode } from "../components/map/RiskMap";
import SimTimeline from "../components/timeline/SimTimeline";
import { ZonePanel } from "../components/zone/ZonePanel";
import ReportModal from "../components/reports/ReportModal";
import DataFreshnessBar from "../components/layout/DataFreshnessBar";
import GovernmentIntelligencePanel from "../components/intelligence/GovernmentIntelligencePanel";
import HotspotRankingPanel from "../components/intelligence/HotspotRankingPanel";
import CriticalSlopeCard from "../components/intelligence/CriticalSlopeCard";
import RainfallScenarioControl from "../components/intelligence/RainfallScenarioControl";
import EmergencyPriorityPanel from "../components/intelligence/EmergencyPriorityPanel";
import WeatherForecast from "../components/zone/WeatherForecast";
import { getZones } from "../api/zones";
import { getRiskMap, getRiskIntensification, getHotspotRanking } from "../api/risk";
import { useUIStore } from "../store/uiStore";
import { useSimClock } from "../hooks/useSimClock";
import { useOnlineStatus } from "../hooks/useOnlineStatus";
import { getLang, setLang, t, type Lang } from "../lib/i18n";
import type { IntensificationResult, Hotspot, SimulationResult } from "../types/risk";

const FLAGSHIP_ZONE_ID = "Z1";

const LANGUAGES: { value: Lang; label: string }[] = [
  { value: "en", label: "EN" },
  { value: "hi", label: "HI" },
  { value: "bn", label: "BN" },
  { value: "kha", label: "KH" },
  { value: "garo", label: "GA" },
];

export default function CommandCenter() {
  const { zoneId } = useParams();
  const simTime = useUIStore((s) => s.simTime);
  const selectZone = useUIStore((s) => s.selectZone);
  useSimClock();
  const online = useOnlineStatus();

  const [zones, setZones] = useState<any[]>([]);
  const [risks, setRisks] = useState<any[]>([]);
  const [reports, setReports] = useState<any[]>([]);
  const [reportOpen, setReportOpen] = useState(false);
  const [intensification, setIntensification] = useState<IntensificationResult[]>([]);
  const [hotspots, setHotspots] = useState<Hotspot[]>([]);
  const [simResults, setSimResults] = useState<SimulationResult[] | null>(null);
  const [sideTab, setSideTab] = useState<"zone" | "intelligence" | "scenario">("zone");
  const [mapMode, setMapMode] = useState<MapMode>("2d");
  const [currentLang, setCurrentLang] = useState<Lang>(getLang());

  useEffect(() => { getZones().then(setZones).catch(() => {}); }, []);
  useEffect(() => {
    import("../api/reports").then((m) => m.getReports().then(setReports).catch(() => {}));
  }, []);

  useEffect(() => {
    getRiskMap(simTime).then((r) => {
      setRisks(r);
      const selected = useUIStore.getState().selectedZoneId;
      if (!selected && !zoneId) {
        const worst = r.reduce((a, b) => (b.risk_score > a.risk_score ? b : a), r[0]);
        if (worst) selectZone(worst.zone_id);
      }
    }).catch(() => {});
    getRiskIntensification(simTime).then((r) => setIntensification(r.intensification)).catch(() => {});
    getHotspotRanking(simTime).then((r) => setHotspots(r.hotspots)).catch(() => {});
  }, [simTime]);

  useEffect(() => { if (zoneId) selectZone(zoneId); }, [zoneId, selectZone]);

  const selectedZoneId = useUIStore((s) => s.selectedZoneId);
  const selectedRisk = risks.find((r) => r.zone_id === selectedZoneId);
  const anyEscalated = risks.some((r) => r.escalated);

  const criticalCount = risks.filter((r) => r.slope_state === "CRITICAL").length;
  const degradingCount = risks.filter((r) => r.slope_state === "DEGRADING").length;

  useEffect(() => { if (selectedZoneId) setSideTab("zone"); }, [selectedZoneId]);

  const handleSimResults = useCallback((results: SimulationResult[]) => {
    setSimResults(results);
    setSideTab("intelligence");
  }, []);

  const handleLangChange = (lang: Lang) => {
    setCurrentLang(lang);
    setLang(lang);
  };

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Top status bar */}
      <div className="flex items-center justify-between border-b border-[#d9e2d9] bg-white px-3 py-1">
        {/* Escalation alert */}
        <div className="flex items-center gap-2">
          {anyEscalated && (
            <>
              <span className="rounded bg-[#ba1a1a] px-1.5 py-0.5 text-[8px] font-bold text-white">ALERT</span>
              <span className="text-[9px] text-[#ba1a1a]">
                <b>ESCALATION ACTIVE</b>
              </span>
              {(criticalCount + degradingCount) > 0 && (
                <span className="text-[8px] font-bold text-[#ba1a1a]">
                  {criticalCount > 0 && `${criticalCount} CRITICAL`}
                  {criticalCount > 0 && degradingCount > 0 && " \u00B7 "}
                  {degradingCount > 0 && `${degradingCount} DEGRADING`}
                </span>
              )}
            </>
          )}
        </div>

        <div className="flex items-center gap-3">
          {/* Language selector */}
          <div className="flex items-center gap-1">
            <span className="text-[7px] text-[#707973]">LANG:</span>
            {LANGUAGES.map((l) => (
              <button
                key={l.value}
                onClick={() => handleLangChange(l.value)}
                className={`rounded px-1 py-0.5 text-[8px] font-bold transition-colors ${
                  currentLang === l.value
                    ? "bg-[#04442f] text-white"
                    : "text-[#707973] hover:bg-[#f0eee6]"
                }`}
              >
                {l.label}
              </button>
            ))}
          </div>

          {/* Online status */}
          <div className="flex items-center gap-1">
            <span className={`h-2 w-2 rounded-full ${online ? "bg-[#245c45]" : "bg-[#d97706]"}`} />
            <span className={`text-[8px] font-bold ${online ? "text-[#245c45]" : "text-[#d97706]"}`}>
              {online ? t("online") : t("offline")}
            </span>
          </div>
        </div>
      </div>

      <div className="relative flex flex-1 overflow-hidden">
        <div className="relative flex-1">
          <RiskMap zones={zones} risks={risks}
            selectedId={selectedZoneId}
            reports={reports}
            intensification={intensification}
            hotspots={hotspots}
            simulationResults={simResults}
            mapMode={mapMode}
            onToggleMode={setMapMode}
            onSelect={(id) => useUIStore.getState().selectZone(id)} />
          <SimTimeline />
        </div>

        <aside className="flex w-[440px] flex-col overflow-y-auto border-l border-[#d9e2d9] bg-[#f0eee6]">
          <DataFreshnessBar />

          {/* Tab bar */}
          <div className="flex border-b border-[#d9e2d9]">
            {(["zone", "intelligence", "scenario"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setSideTab(tab)}
                className={`flex-1 py-1.5 text-[9px] font-bold uppercase tracking-wide transition-colors ${
                  sideTab === tab
                    ? "border-b-2 border-[#04442f] text-[#04442f]"
                    : "text-[#707973] hover:text-[#1b1c17]"
                }`}
              >
                {tab === "zone" ? t("zoneDetail") : tab === "intelligence" ? t("intelligence") : t("scenario")}
              </button>
            ))}
          </div>

          {/* Zone Detail Tab */}
          {sideTab === "zone" && (
            <>
              <button onClick={() => setReportOpen(true)}
                className="mx-3 my-2 rounded-lg bg-[#04442f] py-2 text-xs font-bold text-white hover:bg-[#0a5c40] transition-colors shadow-sm">
                {t("reportLandslip")}
              </button>
              {selectedRisk && selectedRisk.zone_id === FLAGSHIP_ZONE_ID && (
                <div className="mx-3 mb-2 overflow-hidden rounded-lg border border-[#04442f]/30 bg-gradient-to-r from-[#04442f]/5 to-[#0a5c40]/5">
                  <div className="flex items-center gap-2 px-3 py-2">
                    <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#04442f] text-white shadow-sm">
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                        <rect x="2" y="2" width="4" height="4" rx="1" fill="white" opacity="0.8"/>
                        <rect x="6" y="2" width="4" height="4" rx="1" fill="white"/>
                        <rect x="10" y="2" width="4" height="4" rx="1" fill="white" opacity="0.6"/>
                        <rect x="2" y="6" width="4" height="4" rx="1" fill="white" opacity="0.6"/>
                        <rect x="6" y="6" width="4" height="4" rx="1" fill="white" opacity="0.9"/>
                        <rect x="10" y="6" width="4" height="4" rx="1" fill="white" opacity="0.4"/>
                        <rect x="2" y="10" width="4" height="4" rx="1" fill="white" opacity="0.4"/>
                        <rect x="6" y="10" width="4" height="4" rx="1" fill="white" opacity="0.7"/>
                        <rect x="10" y="10" width="4" height="4" rx="1" fill="white" opacity="0.3"/>
                      </svg>
                    </span>
                    <div className="flex-1">
                      <div className="flex items-center gap-1.5">
                        <span className="rounded bg-[#04442f] px-1.5 py-0.5 text-[7px] font-bold text-white uppercase">Deep-Dive Zone</span>
                        <span className="text-[9px] font-bold text-[#04442f]">Sohra (Cherrapunji)</span>
                      </div>
                      <p className="text-[8px] text-[#404943]">
                        Per-cell terrain intelligence active \u2014 RF model runs on each 400m cell
                      </p>
                    </div>
                  </div>
                </div>
              )}
              {selectedRisk ? (
                <div className="space-y-2 p-2">
                  <CriticalSlopeCard />
                  <ZonePanel risk={selectedRisk} zoneId={selectedRisk.zone_id} />
                  <WeatherForecast zoneId={selectedRisk.zone_id} />
                </div>
              ) : (
                <p className="p-4 text-xs text-[#707973]">Select a zone on the map.</p>
              )}
            </>
          )}

          {/* Intelligence Tab */}
          {sideTab === "intelligence" && (
            <div className="space-y-2 p-2">
              <EmergencyPriorityPanel />
              <GovernmentIntelligencePanel />
              <HotspotRankingPanel />
            </div>
          )}

          {/* Scenario Tab */}
          {sideTab === "scenario" && (
            <div className="space-y-2 p-2">
              <div className="rounded-lg border border-[#d97706]/20 bg-[#d97706]/5 px-3 py-2">
                <div className="flex items-center gap-2">
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="text-[#92400e]">
                    <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1"/>
                    <path d="M7 4v3.5M7 9.5v0" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
                  </svg>
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-wide text-[#92400e]">
                      {t("whatIf")}
                    </p>
                    <p className="text-[8px] text-[#707973]">
                      Drag the slider to see real-time risk changes on the map
                    </p>
                  </div>
                </div>
              </div>
              <RainfallScenarioControl onResults={handleSimResults} />
            </div>
          )}
        </aside>

        <ReportModal open={reportOpen} onClose={() => setReportOpen(false)} />
      </div>
    </div>
  );
}

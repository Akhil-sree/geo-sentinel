import { useEffect, useState, useCallback } from "react";
import { useParams } from "react-router-dom";
import RiskMap from "../components/map/RiskMap";
import SimTimeline from "../components/timeline/SimTimeline";
import { ZonePanel } from "../components/zone/ZonePanel";
import ReportModal from "../components/reports/ReportModal";
import DataFreshnessBar from "../components/layout/DataFreshnessBar";
import GovernmentIntelligencePanel from "../components/intelligence/GovernmentIntelligencePanel";
import HotspotRankingPanel from "../components/intelligence/HotspotRankingPanel";
import CriticalSlopeCard from "../components/intelligence/CriticalSlopeCard";
import RainfallScenarioControl from "../components/intelligence/RainfallScenarioControl";
import { getZones } from "../api/zones";
import { getRiskMap, getRiskIntensification, getHotspotRanking } from "../api/risk";
import { useUIStore } from "../store/uiStore";
import { useSimClock } from "../hooks/useSimClock";
import type { IntensificationResult, Hotspot, SimulationResult } from "../types/risk";

export default function CommandCenter() {
  const { zoneId } = useParams();
  const simTime = useUIStore((s) => s.simTime);
  const selectZone = useUIStore((s) => s.selectZone);
  useSimClock();

  const [zones, setZones] = useState<any[]>([]);
  const [risks, setRisks] = useState<any[]>([]);
  const [reports, setReports] = useState<any[]>([]);
  const [reportOpen, setReportOpen] = useState(false);
  const [intensification, setIntensification] = useState<IntensificationResult[]>([]);
  const [hotspots, setHotspots] = useState<Hotspot[]>([]);
  const [simResults, setSimResults] = useState<SimulationResult[] | null>(null);
  const [sideTab, setSideTab] = useState<"zone" | "intelligence" | "scenario">("zone");

  useEffect(() => { getZones().then(setZones).catch(() => {}); }, []);
  useEffect(() => {
    import("../api/reports").then((m) => m.getReports().then(setReports).catch(() => {}));
  }, []);

  useEffect(() => {
    getRiskMap(simTime).then((r) => {
      setRisks(r);
      // Auto-select worst zone if nothing selected
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

  useEffect(() => {
    if (selectedZoneId) setSideTab("zone");
  }, [selectedZoneId]);

  const handleSimResults = useCallback((results: SimulationResult[]) => {
    setSimResults(results);
    setSideTab("intelligence");
  }, []);

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {anyEscalated && (
        <div className="mx-3 mt-1.5 flex items-center gap-2 rounded border border-[#ba1a1a] bg-white px-3 py-1.5">
          <span className="rounded bg-[#ba1a1a] px-1.5 py-0.5 text-[9px] font-bold text-white">ALERT</span>
          <span className="text-[10px] text-[#ba1a1a]">
            <b>ESCALATION RULE ACTIVE</b> — Environmental stress exceeding thresholds
          </span>
          {(criticalCount + degradingCount) > 0 && (
            <span className="ml-auto text-[9px] font-bold text-[#ba1a1a]">
              {criticalCount > 0 && `${criticalCount} CRITICAL`}
              {criticalCount > 0 && degradingCount > 0 && " · "}
              {degradingCount > 0 && `${degradingCount} DEGRADING`}
            </span>
          )}
        </div>
      )}

      <div className="relative flex flex-1 overflow-hidden">
        <div className="relative flex-1">
          <RiskMap zones={zones} risks={risks}
            selectedId={selectedZoneId}
            reports={reports}
            intensification={intensification}
            hotspots={hotspots}
            simulationResults={simResults}
            onSelect={(id) => useUIStore.getState().selectZone(id)} />
          <SimTimeline />
        </div>

        <aside className="flex w-[440px] flex-col overflow-y-auto border-l border-[#d9e2d9] bg-[#f0eee6]">
          <DataFreshnessBar />

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
                {tab === "zone" ? "Zone Detail" : tab === "intelligence" ? "Intelligence" : "Scenario"}
              </button>
            ))}
          </div>

          {sideTab === "zone" && (
            <>
              <button onClick={() => setReportOpen(true)}
                className="mx-3 my-2 rounded bg-[#04442f] py-2 text-xs font-bold text-white hover:bg-[#0a5c40]">
                + REPORT LANDSLIP
              </button>
              {selectedRisk ? (
                <div className="space-y-2 p-2">
                  <CriticalSlopeCard />
                  <ZonePanel risk={selectedRisk} zoneId={selectedRisk.zone_id} />
                </div>
              ) : (
                <p className="p-4 text-xs text-[#707973]">Select a zone on the map.</p>
              )}
            </>
          )}

          {sideTab === "intelligence" && (
            <div className="space-y-2 p-2">
              <GovernmentIntelligencePanel />
              <HotspotRankingPanel />
            </div>
          )}

          {sideTab === "scenario" && (
            <div className="space-y-2 p-2">
              <RainfallScenarioControl onResults={handleSimResults} />
            </div>
          )}
        </aside>

        <ReportModal open={reportOpen} onClose={() => setReportOpen(false)} />
      </div>
    </div>
  );
}

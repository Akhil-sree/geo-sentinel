import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import RiskMap from "../components/map/RiskMap";
import SimTimeline from "../components/timeline/SimTimeline";
import { ZonePanel } from "../components/zone/ZonePanel";
import ReportModal from "../components/reports/ReportModal";
import DataFreshnessBar from "../components/layout/DataFreshnessBar";
import { getZones } from "../api/zones";
import { getRiskMap } from "../api/risk";
import { useUIStore } from "../store/uiStore";
import { useSimClock } from "../hooks/useSimClock";

export default function CommandCenter() {
  const { zoneId } = useParams();
  const simTime = useUIStore((s) => s.simTime);
  const selectZone = useUIStore((s) => s.selectZone);
  useSimClock();

  const [zones, setZones] = useState<any[]>([]);
  const [risks, setRisks] = useState<any[]>([]);
  const [reports, setReports] = useState<any[]>([]);
  const [reportOpen, setReportOpen] = useState(false);

  useEffect(() => { getZones().then(setZones).catch(() => {}); }, []);
  useEffect(() => {
    import("../api/reports").then((m) => m.getReports().then(setReports).catch(() => {}));
  }, []);

  // full pipeline re-run server-side on every scrubber move
  useEffect(() => {
    getRiskMap(simTime).then(setRisks).catch(() => {});
  }, [simTime]);

  useEffect(() => { if (zoneId) selectZone(zoneId); }, [zoneId, selectZone]);

  const selectedZoneId = useUIStore((s) => s.selectedZoneId);
  const selectedRisk = risks.find((r) => r.zone_id === selectedZoneId);
  const anyEscalated = risks.some((r) => r.escalated);

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* escalation strip above content — white/red government-briefing style */}
      {anyEscalated && (
        <div className="mx-3 mt-1.5 flex items-center gap-2 rounded border border-[#ba1a1a] bg-white px-3 py-1.5">
          <span className="rounded bg-[#ba1a1a] px-1.5 py-0.5 text-[9px] font-bold text-white">▲ ALERT</span>
          <span className="text-[10px] text-[#ba1a1a]">
            <b>ESCALATION RULE ACTIVE</b> — Mamba dynamic rise + rainfall trigger
            (calibration rule, not a validated constant)
          </span>
        </div>
      )}

      <div className="relative flex flex-1 overflow-hidden">
        <div className="relative flex-1">
          <RiskMap zones={zones} risks={risks}
            selectedId={selectedZoneId}
            reports={reports}
            onSelect={(id) => useUIStore.getState().selectZone(id)} />
          <SimTimeline />
        </div>

        <aside className="flex w-[420px] flex-col overflow-y-auto border-l border-[#d9e2d9] bg-[#f0eee6]">
          <DataFreshnessBar />
          <button onClick={() => setReportOpen(true)}
            className="mx-3 my-2 rounded bg-[#04442f] py-2 text-xs font-bold text-white hover:bg-[#0a5c40]">
            + REPORT LANDSLIP
          </button>
          {selectedRisk
            ? <ZonePanel risk={selectedRisk} zoneId={selectedRisk.zone_id} />
            : <p className="p-4 text-xs text-[#707973]">Select a zone on the map.</p>}
        </aside>

        <ReportModal open={reportOpen} onClose={() => setReportOpen(false)} />
      </div>
    </div>
  );
}

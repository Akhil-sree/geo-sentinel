export default function AboutPage() {
  return (
    <main className="max-w-2xl overflow-y-auto p-6 text-sm leading-relaxed text-slate-300">
      <h1 className="mb-2 text-lg font-semibold">About GEO-SENTINEL</h1>
      <div className="space-y-3 text-xs">
        <p><b className="text-amber-400">This is a demo. Zone-level advisory only — never house-level prediction, never evacuation directives.</b></p>
        <p>Risk = 0.5·static (RF on terrain: slope, elevation, lithology proxy, historical events) + 0.5·dynamic (temporal model on rainfall/soil-moisture trajectory), with a calibrated escalation rule. Weights and severity boundaries are calibration parameters, not validated constants — see /admin/model/metrics for served-from-artifact numbers.</p>
        <p>Data honesty: rainfall is DEMO DATA (synthetic monsoon); SMAP soil moisture is a 2-day-latency regional proxy; Sentinel-1 SAR is sparse (days between acquisitions) and detects past change, not live motion. All states are surfaced verbatim in the Data Freshness bar — stale sources are shown, never hidden.</p>
        <p>Citizen reports are PENDING until human moderation; only moderated reports may be marked for training reuse.</p>
        <p>Alerts: severity ≥ HIGH only, advisory language only (EN/HI), masked numbers, full audit log. Production requires an SDMA-authorized directory, DLT-registered sender IDs, and DMDA/SDMA integration.</p>
      </div>
    </main>
  );
}

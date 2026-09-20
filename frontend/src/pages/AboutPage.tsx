export default function AboutPage() {
  return (
    <main className="max-w-2xl overflow-y-auto bg-gs-bg p-6 text-[12px] leading-relaxed text-gs-text">
      <h1 className="mb-2 text-[18px] font-semibold text-gs-text">About Geo-Sentinel</h1>
      <div className="space-y-3 text-[11px] text-gs-text-secondary">
        <p><b className="text-risk-stressed">Zone-level advisory only — never house-level prediction, never evacuation directives.</b></p>
        <p>Risk = 0.4·static (RF on terrain) + 0.6·dynamic (temporal model on rainfall/soil trajectory), plus a threshold escalation rule. Weights and boundaries are unvalidated config parameters — and risk scores are uncalibrated (not probabilities). See /admin/model/metrics for measured numbers and /model/reliability for calibration evidence.</p>
        <p>Data honesty: rainfall is simulated monsoon; SMAP soil moisture is a 2-day-latency regional proxy; Sentinel-1 SAR is sparse (days between acquisitions) and detects past change, not live motion. All states are surfaced verbatim in the Data Status bar — stale sources are shown, never hidden.</p>
        <p>Citizen reports are PENDING until human moderation; only moderated reports may be marked for training reuse.</p>
        <p>Alerts: severity ≥ HIGH only, advisory language only (EN/HI), masked numbers, full audit log. Production requires an SDMA-authorized directory, DLT-registered sender IDs, and DMDA/SDMA integration.</p>
      </div>
    </main>
  );
}

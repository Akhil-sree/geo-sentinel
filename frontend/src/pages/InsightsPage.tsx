import { useEffect, useState } from "react";
import { getModelMetrics, getDataFreshness } from "../api/admin";

export default function InsightsPage() {
  const [metrics, setMetrics] = useState<any>(null);
  const [freshness, setFreshness] = useState<any>(null);

  useEffect(() => {
    getModelMetrics().then(setMetrics).catch(() => {});
    getDataFreshness().then(setFreshness).catch(() => {});
  }, []);

  return (
    <div className="flex flex-1 overflow-y-auto bg-gs-bg p-6">
      <div className="mx-auto max-w-4xl space-y-6">
        <h1 className="text-[18px] font-semibold text-gs-text">Data &amp; Insights</h1>

        {/* Model Metrics */}
        <section className="rounded-card p-5" style={{
          background: 'rgba(255, 255, 255, 0.52)',
          backdropFilter: 'blur(8px)',
          WebkitBackdropFilter: 'blur(8px)',
          border: '1px solid rgba(214, 208, 196, 0.35)',
          boxShadow: '0 2px 12px rgba(42, 51, 45, 0.05)',
        }}>
          <h2 className="mb-3 text-[13px] font-semibold text-gs-text">Model performance</h2>
          {metrics ? (
            <div className="grid grid-cols-2 gap-4 text-[11px]">
              {Object.entries(metrics).map(([k, v]) => (
                <div key={k}>
                  <span className="font-medium text-gs-text-secondary">{k}: </span>
                  <span className="text-gs-text">
                    {typeof v === "number" ? v.toFixed(4) : String(v)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-[11px] text-gs-text-secondary">Loading…</p>
          )}
        </section>

        {/* Data Freshness */}
        <section className="rounded-card p-5" style={{
          background: 'rgba(255, 255, 255, 0.52)',
          backdropFilter: 'blur(8px)',
          WebkitBackdropFilter: 'blur(8px)',
          border: '1px solid rgba(214, 208, 196, 0.35)',
          boxShadow: '0 2px 12px rgba(42, 51, 45, 0.05)',
        }}>
          <h2 className="mb-3 text-[13px] font-semibold text-gs-text">Data sources</h2>
          {freshness ? (
            <div className="space-y-2 text-[11px]">
              {Array.isArray(freshness)
                ? freshness.map((s: any, i: number) => (
                    <div key={i} className="flex justify-between border-b border-gs-border pb-2 last:border-0">
                      <span className="font-medium text-gs-text-secondary">{s.source ?? s.name ?? `Source ${i}`}</span>
                      <span className="text-gs-text">{String(s.status ?? s.detail ?? "OK").replace(/SATELLITE_DEMO|DEMO_DATA/gi, "Standby data").replace(/DEMO/gi, "Standby")}</span>
                    </div>
                  ))
                : Object.entries(freshness).map(([k, v]) => (
                    <div key={k} className="flex justify-between border-b border-gs-border pb-2 last:border-0">
                      <span className="font-medium text-gs-text-secondary">{k}</span>
                      <span className="text-gs-text">{String(v).replace(/SATELLITE_DEMO|DEMO_DATA/gi, "Standby data").replace(/DEMO/gi, "Standby")}</span>
                    </div>
                  ))}
            </div>
          ) : (
            <p className="text-[11px] text-gs-text-secondary">Loading…</p>
          )}
        </section>
      </div>
    </div>
  );
}

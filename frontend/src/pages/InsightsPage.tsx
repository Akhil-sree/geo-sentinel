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
    <div className="flex flex-1 overflow-y-auto bg-[#f0eee6] p-6">
      <div className="mx-auto max-w-4xl space-y-6">
        <h1 className="font-headline text-2xl font-bold text-[#04442f]">Data &amp; Insights</h1>

        {/* Model Metrics */}
        <section className="rounded border border-[#d9e2d9] bg-white p-4">
          <h2 className="mb-3 text-sm font-bold text-[#1b1c17]">Model Performance</h2>
          {metrics ? (
            <div className="grid grid-cols-2 gap-4 text-xs">
              {Object.entries(metrics).map(([k, v]) => (
                <div key={k}>
                  <span className="font-semibold text-[#404943]">{k}: </span>
                  <span className="text-[#1b1c17]">
                    {typeof v === "number" ? v.toFixed(4) : String(v)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-[#707973]">Loading...</p>
          )}
        </section>

        {/* Data Freshness */}
        <section className="rounded border border-[#d9e2d9] bg-white p-4">
          <h2 className="mb-3 text-sm font-bold text-[#1b1c17]">Data Sources</h2>
          {freshness ? (
            <div className="space-y-2 text-xs">
              {Array.isArray(freshness)
                ? freshness.map((s: any, i: number) => (
                    <div key={i} className="flex justify-between border-b border-[#d9e2d9] pb-1">
                      <span className="font-semibold text-[#404943]">{s.source ?? s.name ?? `Source ${i}`}</span>
                      <span className="text-[#1b1c17]">{s.status ?? s.detail ?? "OK"}</span>
                    </div>
                  ))
                : Object.entries(freshness).map(([k, v]) => (
                    <div key={k} className="flex justify-between border-b border-[#d9e2d9] pb-1">
                      <span className="font-semibold text-[#404943]">{k}</span>
                      <span className="text-[#1b1c17]">{String(v)}</span>
                    </div>
                  ))}
            </div>
          ) : (
            <p className="text-xs text-[#707973]">Loading...</p>
          )}
        </section>
      </div>
    </div>
  );
}

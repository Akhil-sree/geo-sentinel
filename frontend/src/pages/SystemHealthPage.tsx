import { useEffect, useState } from "react";
import Card from "../components/common/Card";
import { getMetrics, getAlertLangs, getModelVersions } from "../api/ops";

export default function SystemHealthPage() {
  const [m, setM] = useState<any>(null);
  const [langs, setLangs] = useState<any>(null);
  const [models, setModels] = useState<any>(null);
  useEffect(() => {
    getMetrics().then(setM).catch(() => {});
    getAlertLangs().then(setLangs).catch(() => {});
    getModelVersions().then(setModels).catch(() => {});
  }, []);
  return (
    <main className="overflow-y-auto bg-gs-bg p-6">
      <h1 className="mb-4 text-[18px] font-semibold text-gs-text">System Health & Models</h1>
      <div className="grid gap-4 md:grid-cols-3">
        <Card title="Operational metrics (/api/metrics)">
          {m ? Object.entries(m).map(([k, v]) => (
            <div key={k} className="flex justify-between py-1 text-[12px]">
              <span>{k}</span><b>{String(v)}</b>
            </div>
          )) : <p className="text-[12px]">Loading…</p>}
        </Card>
        <Card title="Alert languages">
          <p className="text-[12px]">Served: {(langs?.served ?? []).join(", ")}</p>
          <p className="text-[11px] text-gs-text-secondary">{langs?.policy}</p>
          {langs && Object.entries(langs.statuses).map(([k, v]) => (
            <div key={k} className="flex justify-between py-1 text-[12px]">
              <span>{k}</span><span>{String(v)}</span>
            </div>
          ))}
        </Card>
        <Card title="Model versions + promotion gate">
          <p className="text-[12px]">Static: {models?.served?.static} · Temporal: {models?.served?.temporal}</p>
          <p className="text-[12px]">Fusion: {models?.served?.fusion}</p>
          <p className="text-[11px] font-semibold text-risk-high">{models?.served?.calibration}</p>
          <p className="mt-1 text-[11px] text-gs-text-secondary">
            Gate: n≥{models?.promotion_gate?.min_dataset_size}, F1≥{models?.promotion_gate?.min_f1} ·
            requires {(models?.promotion_gate?.requires ?? []).join(", ")}
          </p>
        </Card>
      </div>
    </main>
  );
}

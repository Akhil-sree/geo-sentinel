import { useEffect, useState } from "react";
import Card from "../components/common/Card";
import { getDatasets, getDataset, getTemporal, getDataQuality, getModelVersions } from "../api/ops";

const SOURCE_CHIP = (s: string) => {
  const live = ["DOWNLOADED", "REAL", "CONFIGURED", "MANUAL_LOADED"].includes(s);
  const blocked = ["AUTH_REQUIRED", "MANUAL_DOWNLOAD_REQUIRED", "FAILED"].includes(s);
  return (
    <b className={live ? "text-forest" : blocked ? "text-risk-high" : "text-gs-text-secondary"}>
      {s}
    </b>
  );
};

export default function DatasetDashboardPage() {
  const [sets, setSets] = useState<any[]>([]);
  const [ds, setDs] = useState<any>(null);
  const [temporal, setTemporal] = useState<any>(null);
  const [quality, setQuality] = useState<any>(null);
  const [models, setModels] = useState<any>(null);
  useEffect(() => {
    getDatasets().then((d) => {
      setSets(d.datasets ?? []);
      const v = (d.datasets ?? [])[0]?.version;
      if (v) getDataset(v).then(setDs).catch(() => {});
    }).catch(() => {});
    getTemporal().then(setTemporal).catch(() => {});
    getDataQuality().then(setQuality).catch(() => {});
    getModelVersions().then(setModels).catch(() => {});
  }, []);
  const counts = ds?.counts ?? {};
  return (
    <main className="overflow-y-auto bg-gs-bg p-6">
      <h1 className="mb-4 text-[18px] font-semibold text-gs-text">Data & Model Health</h1>
      <div className="grid gap-4 md:grid-cols-3">
        <Card title="Dataset version (immutable releases)">
          {sets.length === 0 && <p className="text-[12px]">No NER datasets yet — run scripts/build_training_dataset.py</p>}
          {sets.map((s) => (
            <div key={s.version} className="border-b border-gs-border py-1.5 text-[12px]">
              <b>{s.version}</b> · {s.region} · {s.status} · n={s.counts?.n} (+{s.counts?.positive}/-{s.counts?.negative})
              <div className="text-[11px] text-gs-text-secondary">{s.checksum} · {s.feature_version}</div>
            </div>
          ))}
          {ds && (
            <div className="mt-2 text-[12px]">
              <p>Splits: train {counts.splits?.train} / val {counts.splits?.val} / test {counts.splits?.test}</p>
              <p>Holdout year: {counts.holdout_year} · Leakage: {ds.leakage?.status}</p>
            </div>
          )}
        </Card>
        <Card title="Sources — REAL / MODELED / MOCK / AUTH_REQUIRED">
          <div className="space-y-1 text-[12px]">
            <div className="flex justify-between"><span>NASA COOLR</span>{SOURCE_CHIP(quality?.coolr?.status ?? "UNAVAILABLE")}</div>
            <div className="flex justify-between"><span>GSI (bharatlas mirror)</span>{SOURCE_CHIP("MANUAL_LOADED")}</div>
            <div className="flex justify-between"><span>Open-Meteo archive</span>{SOURCE_CHIP("REAL")}</div>
            <div className="flex justify-between"><span>SMAP L3</span>{SOURCE_CHIP("AUTH_REQUIRED")}</div>
            <div className="flex justify-between"><span>SRTM 30m</span>{SOURCE_CHIP("REAL")}</div>
            <div className="flex justify-between"><span>Sentinel-1</span>{SOURCE_CHIP("REAL")}<span className="text-[11px]">metadata-only</span></div>
            <div className="flex justify-between"><span>Rainfall/soil</span>{SOURCE_CHIP("MOCK")}</div>
          </div>
          <p className="mt-2 text-[11px] text-gs-text-secondary">
            Temporal (trainable): <b>{temporal?.n}</b> · {temporal?.use}
          </p>
        </Card>
        <Card title="Models + promotion gate">
          <p className="text-[12px]">Static: {models?.served?.static} · Temporal: {models?.served?.temporal}</p>
          <p className="text-[11px] font-semibold text-risk-high">{models?.served?.calibration}</p>
          <p className="mt-1 text-[11px] text-gs-text-secondary">
            NER baselines (EXPERIMENTAL, gate BLOCKED at n=30): see docs/ML_FINAL_REPORT.md
          </p>
        </Card>
      </div>
    </main>
  );
}

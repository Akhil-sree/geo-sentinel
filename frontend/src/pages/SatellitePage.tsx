import { useEffect, useState } from "react";
import Card from "../components/common/Card";
import { getSatStatus, getSatScenes, getInventory } from "../api/ops";

export default function SatellitePage() {
  const [status, setStatus] = useState<any>(null);
  const [scenes, setScenes] = useState<any>(null);
  const [inv, setInv] = useState<any>(null);
  useEffect(() => {
    getSatStatus().then(setStatus).catch(() => {});
    getSatScenes().then(setScenes).catch(() => {});
    getInventory().then(setInv).catch(() => {});
  }, []);
  return (
    <main className="overflow-y-auto bg-gs-bg p-6">
      <h1 className="mb-4 text-[18px] font-semibold text-gs-text">Satellite & Historical Inventory</h1>
      <div className="grid gap-4 md:grid-cols-2">
        <Card title="Sentinel-1 provider boundary">
          <p className="text-[12px]"><b>{status?.state}</b> — {String(status?.detail ?? "").replace(/SATELLITE_DEMO|DEMO_DATA/gi, "Standby data").replace(/DEMO/gi, "Standby")}</p>
          <p className="mt-1 text-[11px] text-gs-text-secondary">
            {scenes?.note} · {scenes?.n ?? 0} metadata scenes. Imagery is credential-gated;
            change-detection runs via POST /api/satellite/change (experimental, quarantined from risk).
          </p>
        </Card>
        <Card title="Landslide inventory — spatial vs temporal split">
          <p className="text-[12px]">Temporal (dated, trainable): <b>{inv?.temporal?.n}</b> · {inv?.temporal?.use}</p>
          <p className="text-[12px]">Spatial (display-only): <b>{inv?.spatial?.n}</b> · {inv?.spatial?.use}</p>
          <p className="mt-1 text-[11px] text-gs-text-secondary">{inv?.provenance}</p>
        </Card>
      </div>
    </main>
  );
}

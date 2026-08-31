import { useEffect, useState } from "react";
import { getZones } from "../../api/zones";
import { api } from "../../api/client";

export default function TerrainFacts({ zoneId }: { zoneId: string }) {
  const [zone, setZone] = useState<any>(null);
  const [sar, setSar] = useState<any>(null);

  useEffect(() => {
    getZones().then((zs) => setZone(zs.find((z) => z.id === zoneId)));
    api.get(`/risk/${zoneId}/satellite`).then((r) => setSar(r.data));
  }, [zoneId]);

  if (!zone) return null;
  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
      {[["Slope", `${zone.slope}°`],
        ["Elevation", `${zone.elevation} m`],
        ["Population (exposure)", zone.population.toLocaleString()],
        ["SAR change score", String(zone.sar_change_score)]].map(([k, v]) => (
        <div key={k} className="flex justify-between border-b border-slate-800/60 pb-1">
          <span className="text-slate-500">{k}</span>
          <span className="font-mono">{v}</span>
        </div>
      ))}
      {sar && (
        <div className="col-span-2 rounded bg-slate-900 p-2 text-[11px] leading-relaxed text-slate-400">
          Sentinel-1 acquisition: <b className="font-mono text-slate-300">{sar.acquisition_date ?? "none"}</b>
          {sar.previous_acquisition_date && <> · previous: {sar.previous_acquisition_date}</>}<br />
          <span className="text-amber-400">{sar.honesty_note}</span>
        </div>
      )}
    </div>
  );
}

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
    <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-[12px]">
      {[["Slope", `${zone.slope}°`],
        ["Elevation", `${zone.elevation} m`],
        ["Population", zone.population.toLocaleString()],
        ["SAR change", String(zone.sar_change_score)]].map(([k, v]) => (
        <div key={k} className="flex justify-between border-b border-gs-border/50 pb-1.5">
          <span className="text-gs-text-secondary">{k}</span>
          <span className="font-medium text-gs-text">{v}</span>
        </div>
      ))}
      {sar && (
        <div className="col-span-2 rounded-card bg-navy-950 p-3 text-[12px] leading-relaxed text-gs-text-secondary">
          Sentinel-1 acquisition: <b className="font-medium text-white">{sar.acquisition_date ?? "none"}</b>
          {sar.previous_acquisition_date && <> · previous: {sar.previous_acquisition_date}</>}<br />
          <span className="text-risk-stressed">{sar.honesty_note}</span>
        </div>
      )}
    </div>
  );
}

import { useEffect, useState } from "react";
import { getZones } from "../../api/zones";
import { api } from "../../api/client";
import { t } from "../../lib/i18n";

function getRoadStatus(proximity: number): { label: string; color: string; desc: string } {
  if (proximity >= 0.7) return { label: "GOOD", color: "#245c45", desc: "Accessible by road" };
  if (proximity >= 0.5) return { label: "LIMITED", color: "#d97706", desc: "Single access route" };
  return { label: "POOR", color: "#ba1a1a", desc: "Remote, limited access" };
}

export default function TerrainFacts({ zoneId }: { zoneId: string }) {
  const [zone, setZone] = useState<any>(null);
  const [sar, setSar] = useState<any>(null);

  useEffect(() => {
    getZones().then((zs) => setZone(zs.find((z) => z.id === zoneId)));
    api.get(`/risk/${zoneId}/satellite`).then((r) => setSar(r.data));
  }, [zoneId]);

  if (!zone) return null;

  const roadStatus = getRoadStatus(zone.road_proximity ?? 0.5);

  return (
    <div className="space-y-2 text-[9px]">
      {/* Road Connectivity — prominent display */}
      <div className="rounded border p-2" style={{ borderColor: roadStatus.color + "30", backgroundColor: roadStatus.color + "08" }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span className="text-sm" style={{ color: roadStatus.color }}>
              {roadStatus.color === "#245c45" ? "\u2713" : roadStatus.color === "#ba1a1a" ? "\u26D4" : "\u26A0"}
            </span>
            <div>
              <p className="text-[8px] font-bold uppercase tracking-wider" style={{ color: roadStatus.color }}>
                {t("roadConnectivity")}
              </p>
              <p className="text-[7px] text-[#707973]">{roadStatus.desc}</p>
            </div>
          </div>
          <span className="rounded px-1.5 py-0.5 text-[8px] font-bold text-white" style={{ backgroundColor: roadStatus.color }}>
            {roadStatus.label}
          </span>
        </div>
        {/* Road proximity bar */}
        <div className="mt-1.5">
          <div className="flex justify-between text-[7px] text-[#707973] mb-0.5">
            <span>Road access index</span>
            <span className="font-bold" style={{ color: roadStatus.color }}>{((zone.road_proximity ?? 0) * 100).toFixed(0)}%</span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-[#e4e3db]">
            <div className="h-1.5 rounded-full" style={{ width: `${(zone.road_proximity ?? 0) * 100}%`, backgroundColor: roadStatus.color }} />
          </div>
        </div>
      </div>

      {/* Other terrain facts */}
      <div className="grid grid-cols-2 gap-x-3 gap-y-1">
        {[
          ["Slope", `${zone.slope}\u00B0`],
          ["Elevation", `${zone.elevation} m`],
          [t("ruggedness"), (zone.ruggedness ?? 0).toFixed(2)],
          [t("drainage"), zone.drainage_proximity?.toFixed(2) ?? "—"],
          ["Population", (zone.population ?? 0).toLocaleString()],
          ["SAR Change", zone.sar_change_score?.toFixed(2) ?? "—"],
        ].map(([k, v]) => (
          <div key={k} className="flex justify-between border-b border-[#e4e3db] pb-0.5">
            <span className="text-[8px] text-[#707973]">{k}</span>
            <span className="text-[8px] font-bold text-[#1b1c17]">{v}</span>
          </div>
        ))}
      </div>

      {sar && (
        <div className="rounded border border-[#e4e3db] bg-[#f8f7f3] p-1.5 text-[8px] text-[#707973]">
          Sentinel-1: <span className="font-bold text-[#1b1c17]">{sar.acquisition_date ?? "none"}</span>
          {sar.previous_acquisition_date && <> (prev: {sar.previous_acquisition_date})</>}
          <br /><span className="text-[#92400e]">{sar.honesty_note}</span>
        </div>
      )}
    </div>
  );
}

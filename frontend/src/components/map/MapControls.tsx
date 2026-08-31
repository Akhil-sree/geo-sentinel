import { useMap } from "react-leaflet";
import { useEffect } from "react";
import { useUIStore } from "../../store/uiStore";
import type { Zone } from "../../types/zone";

/** Zooms to the selected zone; Reset button restores regional view. */
export default function MapControls({ zones }: { zones: Zone[] }) {
  const map = useMap();
  const selectedZoneId = useUIStore((s) => s.selectedZoneId);

  useEffect(() => {
    const z = zones.find((z) => z.id === selectedZoneId);
    if (z) map.flyTo([z.lat, z.lng], 10, { duration: 0.8 });
  }, [selectedZoneId, zones, map]);

  return (
    <div className="leaflet-top leaflet-right">
      <button onClick={() => map.flyTo([25.45, 91.1], 8, { duration: 0.8 })}
        className="m-3 rounded border border-slate-700 bg-[#0d1526]/95 px-2 py-1
                   text-[10px] text-slate-300 hover:bg-slate-800">
        ⌂ Meghalaya
      </button>
    </div>
  );
}

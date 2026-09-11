import { useMap } from "react-leaflet";
import { useEffect } from "react";
import { useUIStore } from "../../store/uiStore";
import type { Zone } from "../../types/zone";
import type { MapMode } from "./RiskMap";

export default function MapControls({ zones, onToggleMode }: { zones: Zone[]; mapMode?: MapMode; onToggleMode?: (mode: MapMode) => void }) {
  const map = useMap();
  const selectedZoneId = useUIStore((s) => s.selectedZoneId);

  useEffect(() => {
    const z = zones.find((z) => z.id === selectedZoneId);
    if (z) map.flyTo([z.lat, z.lng], 10, { duration: 0.8 });
  }, [selectedZoneId, zones, map]);

  return (
    <div className="leaflet-top leaflet-right">
      <div className="leaflet-control" style={{ display: "flex", flexDirection: "column", gap: "6px", border: "none", background: "none", boxShadow: "none" }}>
      <button
        onClick={() => map.flyTo([25.45, 91.1], 8, { duration: 0.8 })}
        style={{
          background: "#0d1526",
          border: "1px solid #475569",
          padding: "4px 8px",
          fontSize: "11px",
          color: "#cbd5e1",
          borderRadius: "4px",
          cursor: "pointer",
          pointerEvents: "auto",
        }}
      >
        ⌂ Meghalaya
      </button>
      {onToggleMode && (
        <button
          onClick={() => onToggleMode("3d")}
          style={{
            background: "white",
            border: "1px solid rgba(4,68,47,0.3)",
            padding: "6px 8px",
            fontSize: "11px",
            fontWeight: "700",
            color: "#04442f",
            borderRadius: "6px",
            cursor: "pointer",
            boxShadow: "0 2px 8px rgba(0,0,0,0.2)",
            pointerEvents: "auto",
          }}
        >
          ⛰ 3D TERRAIN
        </button>
      )}
      </div>
    </div>
  );
}

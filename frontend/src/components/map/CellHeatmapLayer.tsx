import { useEffect, useState, useMemo } from "react";
import { CircleMarker } from "react-leaflet";
import { getCellGrid } from "../../api/risk";
import { useUIStore } from "../../store/uiStore";
import type { CellData } from "../../api/risk";
import type { Zone } from "../../types/zone";

const FLAGSHIP_ZONE = "Z1";

interface CellHeatmapLayerProps {
  zones: Zone[];
}

export default function CellHeatmapLayer({ zones }: CellHeatmapLayerProps) {
  const [cells, setCells] = useState<CellData[]>([]);
  const [visible, setVisible] = useState(false);
  const simTime = useUIStore((s) => s.simTime);
  const selectedZoneId = useUIStore((s) => s.selectedZoneId);

  const flagshipZone = useMemo(
    () => zones.find((z) => z.id === FLAGSHIP_ZONE),
    [zones]
  );

  useEffect(() => {
    if (!flagshipZone) return;
    getCellGrid(FLAGSHIP_ZONE, simTime, 18)
      .then((r) => { setCells(r.cells); setVisible(true); })
      .catch(() => setVisible(false));
  }, [flagshipZone, simTime]);

  // Show cells only when flagship zone is selected or hovered
  const showCells = visible && (selectedZoneId === FLAGSHIP_ZONE || !selectedZoneId);

  if (!flagshipZone || !showCells || cells.length === 0) return null;

  const maxRisk = Math.max(...cells.map((c) => c.risk_score), 0.01);

  return (
    <>
      {cells.map((cell, i) => {
        const intensity = cell.risk_score / maxRisk;
        const radius = 4 + intensity * 6;
        const opacity = 0.3 + intensity * 0.5;
        const color = cell.slope_state_color;

        return (
          <CircleMarker
            key={`cell-${i}`}
            center={[cell.lat, cell.lng]}
            radius={radius}
            pathOptions={{
              color: "transparent",
              fillColor: color,
              fillOpacity: opacity,
              weight: 0,
            }}
          >
            <CellTooltip cell={cell} />
          </CircleMarker>
        );
      })}
    </>
  );
}

function CellTooltip({ cell }: { cell: CellData }) {
  return (
    <div className="min-w-[140px] text-[9px]">
      <div className="mb-0.5 flex items-center gap-1">
        <span className="h-2 w-2 rounded-full" style={{ backgroundColor: cell.slope_state_color }} />
        <span className="font-bold" style={{ color: cell.slope_state_color }}>
          {cell.slope_state}
        </span>
      </div>
      <p>Risk: <span className="font-bold">{(cell.risk_score * 100).toFixed(1)}%</span></p>
      <p>Stress: {(cell.stress_score * 100).toFixed(0)}%</p>
      {cell.escalated && <p className="font-bold text-[#ba1a1a]">ESC</p>}
    </div>
  );
}

export { FLAGSHIP_ZONE };

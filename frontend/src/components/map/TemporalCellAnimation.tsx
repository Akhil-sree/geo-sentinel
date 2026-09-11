import { useEffect, useState } from "react";
import { CircleMarker, Tooltip } from "react-leaflet";
import { getTemporalCellGrid } from "../../api/risk";
import { useUIStore } from "../../store/uiStore";
import type { CellData } from "../../api/risk";

const FLAGSHIP_ZONE = "Z1";

interface TemporalFrame {
  t: number;
  label: string;
  cells: CellData[];
}

export default function TemporalCellAnimation({ visible }: { visible: boolean }) {
  const [frames, setFrames] = useState<TemporalFrame[]>([]);
  const [frameIdx, setFrameIdx] = useState(-1);
  const selectedZoneId = useUIStore((s) => s.selectedZoneId);

  useEffect(() => {
    if (!visible || selectedZoneId !== FLAGSHIP_ZONE) return;
    getTemporalCellGrid(FLAGSHIP_ZONE, 14)
      .then((r) => { setFrames(r.timesteps); setFrameIdx(r.timesteps.length - 1); })
      .catch(() => {});
  }, [visible, selectedZoneId]);

  if (!visible || selectedZoneId !== FLAGSHIP_ZONE || frames.length === 0) return null;

  const frame = frames[frameIdx] ?? frames[frames.length - 1];
  const maxRisk = Math.max(...frame.cells.map((c) => c.risk_score), 0.01);

  return (
    <>
      {frame.cells.map((cell, i) => {
        const intensity = cell.risk_score / maxRisk;
        const radius = 3 + intensity * 5;
        return (
          <CircleMarker
            key={`temporal-${i}`}
            center={[cell.lat, cell.lng]}
            radius={radius}
            pathOptions={{
              color: "transparent",
              fillColor: cell.slope_state_color,
              fillOpacity: 0.25 + intensity * 0.55,
              weight: 0,
            }}
          >
            <Tooltip direction="top">
              <div className="text-[9px]">
                <b>{frame.label}</b> — Risk: {(cell.risk_score * 100).toFixed(1)}%
                <br />{cell.slope_state}
              </div>
            </Tooltip>
          </CircleMarker>
        );
      })}
    </>
  );
}

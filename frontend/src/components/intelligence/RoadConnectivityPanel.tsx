import { useEffect, useState } from "react";
import { getRoads } from "../../api/dashboard";
import Spinner from "../common/Spinner";
import type { RoadSegment } from "../../types/risk";

const STATUS_COLORS: Record<string, string> = {
  OPEN: "#2563EB",
  BLOCKED: "#ba1a1a",
  DAMAGED: "#ea580c",
  UNDER_REPAIR: "#d97706",
};

export default function RoadConnectivityPanel() {
  const [roads, setRoads] = useState<RoadSegment[]>([]);
  const [summary, setSummary] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getRoads()
      .then((data) => {
        setRoads(data.roads || []);
        setSummary(data.summary || "");
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="rounded-lg p-4" style={{ background: '#FFFFFF', border: '1px solid #E5E7EB' }}>
        <div className="flex items-center gap-2 text-[14px] text-gs-text-secondary"><Spinner /> Loading roads...</div>
      </div>
    );
  }

  if (!roads.length) return null;

  return (
    <div className="rounded-card p-4" style={{ background: 'rgba(229, 233, 224, 0.45)', backdropFilter: 'blur(8px)', border: '1px solid rgba(255,255,255,0.18)' }}>
      <h3 className="text-[15px] font-bold text-gs-text mb-1">Road Connectivity</h3>
      <p className="text-[12px] text-gs-text-secondary mb-3">{summary}</p>

      {/* Status summary */}
      <div className="flex gap-2 mb-3">
        {Object.entries(STATUS_COLORS).map(([status, color]) => {
          const count = roads.filter((r) => r.status === status).length;
          if (count === 0) return null;
          return (
            <span key={status} className="px-2 py-1 rounded-full text-[11px] font-bold text-white" style={{ background: color }}>
              {count} {status.replace("_", " ")}
            </span>
          );
        })}
      </div>

      {/* Road list */}
      <div className="space-y-1.5 max-h-60 overflow-y-auto">
        {roads.map((road) => (
          <div key={road.id} className="flex items-center justify-between rounded-lg px-3 py-2" style={{ background: '#F9FAFB', borderLeft: `3px solid ${STATUS_COLORS[road.status]}` }}>
            <div className="flex-1">
              <div className="text-[13px] font-semibold text-gs-text">{road.name}</div>
              <div className="text-[11px] text-gs-text-secondary">{road.from_zone} → {road.to_zone} · {road.length_km} km</div>
            </div>
            <div className="text-right">
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold text-white" style={{ background: STATUS_COLORS[road.status] }}>
                {road.status.replace("_", " ")}
              </span>
              {road.blockage_reason && (
                <div className="text-[10px] text-gs-text-secondary mt-0.5">{road.blockage_reason}</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

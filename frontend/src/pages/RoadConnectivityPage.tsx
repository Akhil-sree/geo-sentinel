import { useEffect, useState } from "react";
import { getRoads } from "../api/dashboard";
import Spinner from "../components/common/Spinner";
import type { RoadSegment } from "../types/risk";

const STATUS_COLORS: Record<string, string> = {
  OPEN: "#2563EB",
  BLOCKED: "#ba1a1a",
  DAMAGED: "#ea580c",
  UNDER_REPAIR: "#d97706",
};

export default function RoadConnectivityPage() {
  const [roads, setRoads] = useState<RoadSegment[]>([]);
  const [summary, setSummary] = useState("");
  const [total, setTotal] = useState(0);
  const [blockedCount, setBlockedCount] = useState(0);
  const [openCount, setOpenCount] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getRoads()
      .then((data) => {
        setRoads(data.roads || []);
        setSummary(data.summary || "");
        setTotal(data.total || 0);
        setBlockedCount(data.blocked || 0);
        setOpenCount(data.open || 0);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const damagedCount = roads.filter((r) => r.status === "DAMAGED").length;

  return (
    <div className="flex flex-1 flex-col overflow-y-auto p-6" style={{ background: '#F4F5F0' }}>
      <div className="mx-auto w-full max-w-5xl">
        <div className="mb-6">
          <h1 className="text-[28px] font-bold" style={{ color: '#1A3C2E' }}>Road Connectivity</h1>
          <p className="text-[14px] mt-1" style={{ color: '#6B7280' }}>{summary || "Zone-to-zone road connectivity status from backend monitoring"}</p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Spinner /><span className="ml-3 text-[16px]" style={{ color: '#6B7280' }}>Loading...</span>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-4 gap-4 mb-6">
              <div className="rounded-xl p-4" style={{ background: '#FFFFFF', border: '1px solid #E5E7EB' }}>
                <div className="text-[28px] font-bold" style={{ color: '#1A3C2E' }}>{total}</div>
                <div className="text-[13px]" style={{ color: '#6B7280' }}>Total Roads</div>
              </div>
              <div className="rounded-xl p-4" style={{ background: '#FFFFFF', border: '1px solid #E5E7EB' }}>
                <div className="text-[28px] font-bold" style={{ color: '#2563EB' }}>{openCount}</div>
                <div className="text-[13px]" style={{ color: '#6B7280' }}>Open</div>
              </div>
              <div className="rounded-xl p-4" style={{ background: '#FFFFFF', border: '1px solid #E5E7EB' }}>
                <div className="text-[28px] font-bold" style={{ color: '#ba1a1a' }}>{blockedCount}</div>
                <div className="text-[13px]" style={{ color: '#6B7280' }}>Blocked</div>
              </div>
              <div className="rounded-xl p-4" style={{ background: '#FFFFFF', border: '1px solid #E5E7EB' }}>
                <div className="text-[28px] font-bold" style={{ color: '#ea580c' }}>{damagedCount}</div>
                <div className="text-[13px]" style={{ color: '#6B7280' }}>Damaged</div>
              </div>
            </div>

            <div className="rounded-xl overflow-hidden" style={{ background: '#FFFFFF', border: '1px solid #E5E7EB' }}>
              <table className="w-full">
                <thead>
                  <tr style={{ background: '#F9FAFB', borderBottom: '1px solid #E5E7EB' }}>
                    <th className="px-4 py-3 text-left text-[13px] font-semibold" style={{ color: '#6B7280' }}>Road Name</th>
                    <th className="px-4 py-3 text-left text-[13px] font-semibold" style={{ color: '#6B7280' }}>From → To</th>
                    <th className="px-4 py-3 text-left text-[13px] font-semibold" style={{ color: '#6B7280' }}>Length</th>
                    <th className="px-4 py-3 text-left text-[13px] font-semibold" style={{ color: '#6B7280' }}>Type</th>
                    <th className="px-4 py-3 text-left text-[13px] font-semibold" style={{ color: '#6B7280' }}>Status</th>
                    <th className="px-4 py-3 text-left text-[13px] font-semibold" style={{ color: '#6B7280' }}>Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {roads.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-[14px]" style={{ color: '#6B7280' }}>
                        No road segments found in the database
                      </td>
                    </tr>
                  ) : (
                    roads.map((road) => (
                      <tr key={road.id} style={{ borderBottom: '1px solid #F3F4F6' }}>
                        <td className="px-4 py-3 text-[13px] font-medium" style={{ color: '#1A3C2E' }}>{road.name}</td>
                        <td className="px-4 py-3 text-[13px]" style={{ color: '#6B7280' }}>{road.from_zone} → {road.to_zone}</td>
                        <td className="px-4 py-3 text-[13px]" style={{ color: '#6B7280' }}>{road.length_km} km</td>
                        <td className="px-4 py-3 text-[13px]" style={{ color: '#6B7280' }}>{road.road_type}</td>
                        <td className="px-4 py-3">
                          <span className="inline-block px-2.5 py-1 rounded-full text-[11px] font-bold text-white" style={{ background: STATUS_COLORS[road.status] || '#999' }}>
                            {road.status.replace("_", " ")}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-[12px]" style={{ color: '#6B7280' }}>{road.blockage_reason || "—"}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

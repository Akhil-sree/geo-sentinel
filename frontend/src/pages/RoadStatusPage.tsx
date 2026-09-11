import { useEffect, useState } from "react";
import { getRoadSegments, type RoadSegment } from "../api/dashboard";
import { useUIStore } from "../store/uiStore";
import { t } from "../lib/i18n";

const STATUS_CONFIG: Record<string, { color: string; bg: string; icon: string; label: string }> = {
  OPEN: { color: "#245c45", bg: "#245c4515", icon: "\u2713", label: "Open" },
  BLOCKED: { color: "#ba1a1a", bg: "#ba1a1a15", icon: "\u2717", label: "Blocked" },
  DAMAGED: { color: "#ea580c", bg: "#ea580c15", icon: "\u26A0", label: "Damaged" },
  UNDER_REPAIR: { color: "#d97706", bg: "#d9770615", icon: "\u21BB", label: "Under Repair" },
};

const REASON_LABELS: Record<string, string> = {
  landslide: "Landslide",
  flood: "Flash Flood",
  slope_failure: "Slope Failure",
  maintenance: "Planned Maintenance",
};

export default function RoadStatusPage() {
  const [roads, setRoads] = useState<RoadSegment[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("ALL");
  const selectZone = useUIStore((s) => s.selectZone);

  useEffect(() => {
    getRoadSegments()
      .then((r) => setRoads(r.roads))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = filter === "ALL" ? roads : roads.filter((r) => r.status === filter);
  const blocked = roads.filter((r) => r.status !== "OPEN");

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center bg-[#f0eee6]">
        <div className="text-center">
          <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-[#04442f] border-t-transparent" />
          <p className="text-[11px] text-[#707973]">Loading road data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col overflow-y-auto bg-[#f0eee6]">
      {/* Header */}
      <div className="border-b border-[#d9e2d9] bg-white px-5 py-3">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-[#04442f]">{t("roadConnectivity")}</h1>
            <p className="text-[10px] text-[#707973]">
              Real-time road status across monitored zones
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-[10px] font-bold text-[#1b1c17]">{roads.length} Segments</p>
              <p className="text-[9px] text-[#ba1a1a]">{blocked.length} Disrupted</p>
            </div>
          </div>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-3 px-5 py-3">
        {(["OPEN", "BLOCKED", "DAMAGED", "UNDER_REPAIR"] as const).map((status) => {
          const count = roads.filter((r) => r.status === status).length;
          const cfg = STATUS_CONFIG[status];
          return (
            <button
              key={status}
              onClick={() => setFilter(filter === status ? "ALL" : status)}
              className={`rounded-lg border p-3 text-left transition-all ${
                filter === status
                  ? "ring-2 ring-[#04442f] shadow-sm"
                  : "hover:shadow-sm"
              }`}
              style={{ borderColor: cfg.color + "40", backgroundColor: cfg.bg }}
            >
              <div className="flex items-center gap-2">
                <span
                  className="flex h-8 w-8 items-center justify-center rounded-lg text-white"
                  style={{ backgroundColor: cfg.color }}
                >
                  <span className="text-sm">{cfg.icon}</span>
                </span>
                <div>
                  <p className="text-lg font-bold" style={{ color: cfg.color }}>{count}</p>
                  <p className="text-[9px] font-semibold" style={{ color: cfg.color }}>{cfg.label}</p>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Filter info */}
      {filter !== "ALL" && (
        <div className="mx-5 mb-2 flex items-center gap-2">
          <span className="text-[9px] text-[#707973]">
            Filtered: {STATUS_CONFIG[filter]?.label}
          </span>
          <button
            onClick={() => setFilter("ALL")}
            className="text-[9px] font-bold text-[#ba1a1a] hover:underline"
          >
            Clear
          </button>
        </div>
      )}

      {/* Road list */}
      <div className="space-y-2 px-5 pb-5">
        {filtered.length === 0 ? (
          <div className="rounded-lg border border-[#d9e2d9] bg-white p-8 text-center">
            <p className="text-[11px] text-[#707973]">No road segments match filter.</p>
          </div>
        ) : (
          filtered.map((road) => {
            const cfg = STATUS_CONFIG[road.status];
            return (
              <div
                key={road.id}
                className="overflow-hidden rounded-lg border border-[#d9e2d9] bg-white shadow-sm transition hover:shadow-md"
              >
                <div className="flex items-stretch">
                  {/* Status indicator */}
                  <div
                    className="w-1.5 shrink-0"
                    style={{ backgroundColor: cfg.color }}
                  />

                  <div className="flex-1 p-3">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        {/* Road name + type */}
                        <div className="flex items-center gap-2">
                          <h3 className="text-[11px] font-bold text-[#1b1c17]">
                            {road.name}
                          </h3>
                          <span
                            className="rounded px-1.5 py-0.5 text-[7px] font-bold uppercase"
                            style={{ backgroundColor: cfg.bg, color: cfg.color }}
                          >
                            {road.road_type}
                          </span>
                        </div>

                        {/* Status badge */}
                        <div className="mt-1 flex items-center gap-2">
                          <span
                            className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[9px] font-bold"
                            style={{ backgroundColor: cfg.bg, color: cfg.color, border: `1px solid ${cfg.color}30` }}
                          >
                            {cfg.icon} {cfg.label}
                          </span>
                          {road.blockage_reason && (
                            <span className="text-[9px] text-[#707973]">
                              Reason: {REASON_LABELS[road.blockage_reason] || road.blockage_reason}
                            </span>
                          )}
                        </div>

                        {/* Connection info */}
                        <div className="mt-1.5 flex items-center gap-3 text-[9px] text-[#707973]">
                          <span>
                            <span className="font-semibold text-[#1b1c17]">{road.from_zone}</span>
                            {" \u2192 "}
                            <span className="font-semibold text-[#1b1c17]">{road.to_zone}</span>
                          </span>
                          <span>{road.length_km} km</span>
                        </div>
                      </div>

                      {/* Navigate to zone */}
                      <button
                        onClick={() => selectZone(road.from_zone)}
                        className="ml-3 shrink-0 rounded border border-[#d9e2d9] px-2 py-1 text-[8px] font-bold text-[#04442f] transition hover:bg-[#04442f] hover:text-white"
                      >
                        View Zone
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

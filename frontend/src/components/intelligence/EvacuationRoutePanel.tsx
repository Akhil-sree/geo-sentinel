import { useEffect, useState, useCallback } from "react";
import {
  optimizeRoute,
  getAllRoutesFrom,
  getZonesForRouting,
} from "../../api/dashboard";
import { useUIStore } from "../../store/uiStore";
import { fmtPctOpt } from "../../lib/format";
import Spinner from "../common/Spinner";
import type { EvacuationRoute, ZoneListItem } from "../../types/risk";

const RISK_COLORS: Record<string, string> = {
  LOW: "#2563EB",
  MODERATE: "#d97706",
  HIGH: "#ea580c",
  UNREACHABLE: "#ba1a1a",
};

const STATUS_COLORS: Record<string, string> = {
  OPEN: "#2563EB",
  BLOCKED: "#ba1a1a",
  DAMAGED: "#ea580c",
  UNDER_REPAIR: "#d97706",
};

export default function EvacuationRoutePanel() {
  const selectedZoneId = useUIStore((s) => s.selectedZoneId);
  const simTime = useUIStore((s) => s.simTime);

  const [zones, setZones] = useState<ZoneListItem[]>([]);
  const [source, setSource] = useState("");
  const [target, setTarget] = useState("");
  const [mode, setMode] = useState<"response" | "evacuation">("response");
  const [route, setRoute] = useState<EvacuationRoute | null>(null);
  const [allRoutes, setAllRoutes] = useState<EvacuationRoute[]>([]);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState<"pair" | "from_zone">("pair");

  useEffect(() => {
    getZonesForRouting().then((d) => setZones(d.zones || [])).catch(() => {});
  }, []);

  useEffect(() => {
    if (selectedZoneId && !source) setSource(selectedZoneId);
  }, [selectedZoneId, source]);

  const handleFindRoute = useCallback(() => {
    if (!source || !target || source === target) return;
    setLoading(true);
    setRoute(null);
    setAllRoutes([]);
    optimizeRoute(source, target, mode, simTime)
      .then((r) => setRoute(r))
      .catch(() => setRoute(null))
      .finally(() => setLoading(false));
  }, [source, target, mode, simTime]);

  const handleFindAll = useCallback(() => {
    if (!source) return;
    setLoading(true);
    setRoute(null);
    setAllRoutes([]);
    getAllRoutesFrom(source, mode, simTime)
      .then((d) => setAllRoutes(d.routes || []))
      .catch(() => setAllRoutes([]))
      .finally(() => setLoading(false));
  }, [source, mode, simTime]);

  return (
    <div className="rounded-lg p-4" style={{
      background: '#FFFFFF',
      border: '1px solid #E5E7EB',
    }}>
      <h3 className="text-[15px] font-bold text-gs-text mb-1">Route Optimization</h3>
      <p className="text-[12px] text-gs-text-secondary mb-3">
        Risk-aware A* routing through the road network
      </p>

      {/* Mode selector */}
      <div className="flex gap-1 mb-2">
        <button onClick={() => setMode("response")}
          className={`flex-1 rounded-lg px-3 py-1.5 text-[11px] font-semibold transition ${mode === "response" ? "bg-forest text-white" : "bg-white/40 text-gs-text-secondary hover:bg-white/60"}`}>
          Response Mode
        </button>
        <button onClick={() => setMode("evacuation")}
          className={`flex-1 rounded-lg px-3 py-1.5 text-[11px] font-semibold transition ${mode === "evacuation" ? "bg-forest text-white" : "bg-white/40 text-gs-text-secondary hover:bg-white/60"}`}>
          Evacuation Mode
        </button>
      </div>

      {/* View toggle */}
      <div className="flex gap-1 mb-3">
        <button onClick={() => setViewMode("pair")}
          className={`flex-1 rounded-lg px-3 py-1.5 text-[11px] font-semibold transition ${viewMode === "pair" ? "bg-forest text-white" : "bg-white/40 text-gs-text-secondary hover:bg-white/60"}`}>
          Point-to-Point
        </button>
        <button onClick={() => setViewMode("from_zone")}
          className={`flex-1 rounded-lg px-3 py-1.5 text-[11px] font-semibold transition ${viewMode === "from_zone" ? "bg-forest text-white" : "bg-white/40 text-gs-text-secondary hover:bg-white/60"}`}>
          All Routes From Zone
        </button>
      </div>

      {/* Source */}
      <div className="mb-2">
        <label className="text-[11px] font-semibold text-gs-text-secondary uppercase tracking-wide">
          {viewMode === "pair" ? "From" : "Source Zone"}
        </label>
        <select value={source} onChange={(e) => setSource(e.target.value)}
          className="mt-1 w-full rounded-lg border border-white/30 bg-white/50 px-3 py-2 text-[13px] text-gs-text focus:outline-none focus:ring-2 focus:ring-forest/40">
          <option value="">Select zone...</option>
          {zones.map((z) => <option key={z.id} value={z.id}>{z.id} — {z.name}</option>)}
        </select>
      </div>

      {/* Target */}
      {viewMode === "pair" && (
        <div className="mb-3">
          <label className="text-[11px] font-semibold text-gs-text-secondary uppercase tracking-wide">To</label>
          <select value={target} onChange={(e) => setTarget(e.target.value)}
            className="mt-1 w-full rounded-lg border border-gs-border bg-white px-3 py-2 text-[13px] text-gs-text focus:outline-none focus:ring-2 focus:ring-forest/40">
            <option value="">Select destination...</option>
            {zones.filter((z) => z.id !== source).map((z) => <option key={z.id} value={z.id}>{z.id} — {z.name}</option>)}
          </select>
        </div>
      )}

      <button onClick={viewMode === "pair" ? handleFindRoute : handleFindAll}
        disabled={loading || !source || (viewMode === "pair" && (!target || source === target))}
        className="w-full rounded-card bg-forest py-2.5 text-[13px] font-semibold text-white shadow-sm transition hover:bg-forest-dark active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed">
        {loading ? "Computing..." : viewMode === "pair" ? "Find Lower-Exposure Route" : "Show All Routes"}
      </button>

      {loading && (
        <div className="flex items-center gap-2 mt-3 text-[13px] text-gs-text-secondary">
          <Spinner /> Running A* on road network...
        </div>
      )}

      {/* Single route result */}
      {route && !loading && (
        <div className="mt-3 space-y-2">
          {route.route_available ? (
            <>
              {/* Route summary */}
              <div className="rounded-lg p-3" style={{
                background: '#F9FAFB',
                borderLeft: `3px solid ${RISK_COLORS[route.risk_level]}`,
              }}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[13px] font-bold text-gs-text">
                    {route.source_name} → {route.target_name}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold text-white"
                      style={{ background: RISK_COLORS[route.risk_level] }}>
                      {route.risk_level}
                    </span>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold text-white"
                      style={{ background: route.mode === "evacuation" ? "#ea580c" : "#2563EB" }}>
                      {route.mode.toUpperCase()}
                    </span>
                  </div>
                </div>
                <div className="grid grid-cols-4 gap-2 text-[11px]">
                  <div>
                    <span className="text-gs-text-secondary">Distance</span>
                    <div className="font-bold text-gs-text">{route.distance_km} km</div>
                  </div>
                  <div>
                    <span className="text-gs-text-secondary">ETA</span>
                    <div className="font-bold text-gs-text">~{route.estimated_time_min} min</div>
                  </div>
                  <div>
                    <span className="text-gs-text-secondary">Safety</span>
                    <div className="font-bold text-gs-text">{fmtPctOpt(route.safety_score)}</div>
                  </div>
                  <div>
                    <span className="text-gs-text-secondary">Algorithm</span>
                    <div className="font-bold text-gs-text">{route.algorithm}</div>
                  </div>
                </div>
              </div>

              {/* Path breadcrumb */}
              <div className="flex flex-wrap items-center gap-1 text-[11px] text-gs-text">
                {route.path_names.map((name, i) => (
                  <span key={i} className="flex items-center gap-1">
                    <span className="font-semibold">{name}</span>
                    {i < route.path_names.length - 1 && <span className="text-gs-text-secondary">→</span>}
                  </span>
                ))}
              </div>

              {/* Explanation */}
              {route.explanation && (
                <div className="rounded-lg p-2.5" style={{ background: "#F4F1EB" }}>
                  <div className="text-[11px] font-semibold text-gs-text-secondary uppercase tracking-wide mb-1">
                    Why this route?
                  </div>
                  {route.explanation.why?.map((w, i) => (
                    <div key={i} className="flex items-start gap-1.5 text-[11px] text-gs-text mb-0.5">
                      <span className="text-forest mt-0.5">✓</span> {w}
                    </div>
                  ))}
                  {route.explanation.tradeoffs?.map((t, i) => (
                    <div key={i} className="flex items-start gap-1.5 text-[11px] text-orange-700 mt-1">
                      <span className="mt-0.5">⚠</span> {t}
                    </div>
                  ))}
                </div>
              )}

              {/* Roads used */}
              {route.roads_used.length > 0 && (
                <div className="space-y-1">
                  <div className="text-[11px] font-semibold text-gs-text-secondary uppercase tracking-wide">Roads Used</div>
                  {route.roads_used.map((seg, i) => (
                    <div key={i} className="flex items-center justify-between rounded-lg px-3 py-1.5"
                      style={{ background: "#F9FAFB", borderLeft: `3px solid ${STATUS_COLORS[seg.status]}` }}>
                      <div className="flex-1">
                        <div className="text-[12px] font-semibold text-gs-text">{seg.road_name}</div>
                        <div className="text-[10px] text-gs-text-secondary">{seg.from_name} → {seg.to_name} · {seg.length_km} km</div>
                      </div>
                      <span className="px-2 py-0.5 rounded-full text-[9px] font-bold text-white"
                        style={{ background: STATUS_COLORS[seg.status] }}>
                        {seg.status.replace("_", " ")}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* Roads avoided */}
              {route.roads_avoided.length > 0 && (
                <div>
                  <div className="text-[11px] font-semibold text-gs-text-secondary uppercase tracking-wide mb-1">Roads Avoided</div>
                  <div className="flex flex-wrap gap-1">
                    {route.roads_avoided.map((r, i) => (
                      <span key={i} className="px-2 py-0.5 rounded-full text-[10px] font-medium"
                        style={{ background: STATUS_COLORS[r.status] + "20", color: STATUS_COLORS[r.status] }}>
                        {r.road_name} ({r.status})
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {route.warnings.length > 0 && (
                <div className="rounded-lg bg-orange-50/60 p-2 text-[11px] text-orange-800">
                  <span className="font-bold">Warnings: </span>{route.warnings.join("; ")}
                </div>
              )}
            </>
          ) : (
            /* Not available */
            <div className="rounded-lg p-3" style={{ background: "#FEF2F2", borderLeft: "3px solid #ba1a1a" }}>
              <div className="text-[13px] font-bold text-red-800 mb-1">No Lower-Exposure Route Available</div>
              <div className="text-[11px] text-red-700">{route.reason}</div>
              {route.reachable_zones && route.reachable_zones.length > 0 && (
                <div className="mt-2 text-[11px] text-gs-text-secondary">
                  Reachable zones: <span className="font-semibold text-gs-text">{route.reachable_zones.join(", ")}</span>
                </div>
              )}
              {route.explanation && (
                <div className="mt-2">
                  {route.explanation.why?.map((w, i) => (
                    <div key={i} className="text-[11px] text-gs-text">• {w}</div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* All routes result */}
      {allRoutes.length > 0 && !loading && (
        <div className="mt-3 space-y-2">
          <div className="text-[12px] font-semibold text-gs-text-secondary">
            {allRoutes.length} lower-exposure routes from <span className="text-gs-text">{source}</span> ({mode} mode)
          </div>
          {allRoutes.map((r) => (
            <div key={r.target} className="rounded-lg p-2.5 cursor-pointer transition hover:bg-gs-surface"
              style={{ background: "#F9FAFB", borderLeft: `3px solid ${RISK_COLORS[r.risk_level]}` }}
              onClick={() => { setTarget(r.target); setRoute(r); setViewMode("pair"); }}>
              <div className="flex items-center justify-between">
                <span className="text-[12px] font-semibold text-gs-text">→ {r.target_name}</span>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-gs-text-secondary">{r.distance_km} km · ~{r.estimated_time_min} min · Safety {(r.safety_score * 100).toFixed(0)}%</span>
                  <span className="px-1.5 py-0.5 rounded-full text-[9px] font-bold text-white"
                    style={{ background: RISK_COLORS[r.risk_level] }}>{r.risk_level}</span>
                </div>
              </div>
              <div className="text-[10px] text-gs-text-secondary mt-0.5">{r.path_names.join(" → ")}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

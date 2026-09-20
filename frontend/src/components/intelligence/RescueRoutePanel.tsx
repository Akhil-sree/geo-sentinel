import { useState, useCallback, useMemo, useEffect } from "react";
import { getRescueRoute, type RescueRouteResult, type RescueRouteOption } from "../../api/dashboard";
import { useUIStore } from "../../store/uiStore";
import Spinner from "../common/Spinner";

export interface RescueZoneOption {
  id: string;
  name: string;
  lat: number;
  lng: number;
}

interface RescueRoutePanelProps {
  zones: RescueZoneOption[];
}

function fmtEta(min?: number): string {
  if (min == null || !Number.isFinite(min) || min <= 0) return "—";
  if (min < 60) return `~${Math.round(min)} min`;
  const h = Math.floor(min / 60);
  const m = Math.round(min % 60);
  return m === 0 ? `~${h} h` : `~${h} h ${m} min`;
}

export default function RescueRoutePanel({ zones }: RescueRoutePanelProps) {
  const selectedZoneId = useUIStore((s) => s.selectedZoneId);
  const route = useUIStore((s) => s.rescueRoute);
  const status = useUIStore((s) => s.rescueStatus);
  const journeyPhase = useUIStore((s) => s.journeyPhase);
  const setRescueRoute = useUIStore((s) => s.setRescueRoute);
  const clearRescueRoute = useUIStore((s) => s.clearRescueRoute);
  const setJourneyPhase = useUIStore((s) => s.setJourneyPhase);
  const resetJourney = useUIStore((s) => s.resetJourney);
  const safeZoneRequest = useUIStore((s) => s.safeZoneRequest);
  const setSafeZoneRequest = useUIStore((s) => s.setSafeZoneRequest);

  const selectedRiskZone = useMemo(
    () => zones.find((z) => z.id === selectedZoneId) ?? null,
    [zones, selectedZoneId]
  );

  const defaultFrom = selectedZoneId ?? zones[0]?.id ?? "Z1";
  const [fromId, setFromId] = useState(defaultFrom);
  const [toId, setToId] = useState(
    zones.find((z) => z.id !== defaultFrom)?.id ?? ""
  );
  const [showRoads, setShowRoads] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Map selection drives the origin (§21: new selection clears the old route
  // via the store, then the user recalculates from here).
  useEffect(() => {
    if (selectedZoneId) setFromId(selectedZoneId);
  }, [selectedZoneId]);

  const storeResult = useCallback((result: RescueRouteResult, originName: string, fallbackDest: string) => {
    const named: RescueRouteResult = {
      ...result,
      originName,
      destName: result.destination?.name ?? fallbackDest,
    };
    const coords = result.route_geometry ?? result.geometry?.coordinates ?? [];
    if (result.route_available && coords.length >= 2) {
      setRescueRoute(named, "success");
    } else {
      setRescueRoute(named, "unavailable");
    }
  }, [setRescueRoute]);
  const fromZone = useMemo(
    () => zones.find((z) => z.id === fromId),
    [zones, fromId]
  );
  const toZone = useMemo(
    () => zones.find((z) => z.id === toId),
    [zones, toId]
  );
  const sameZone = fromId !== "" && fromId === toId;

  const handleFindRoute = useCallback(() => {
    if (!fromZone || !toZone || sameZone) return;
    setError(null);
    setRescueRoute(null, "calculating");
    getRescueRoute(fromZone.lat, fromZone.lng, toZone.lat, toZone.lng)
      .then((result: RescueRouteResult) => storeResult(result, fromZone.name, toZone.name))
      .catch(() => {
        setError("Routing service unreachable — is the backend running on :8000?");
        setRescueRoute(null, "error");
      });
  }, [fromZone, toZone, sameZone, setRescueRoute, storeResult]);

  // Risk zone → nearest reachable safe zone (backend auto-selects;
  // destination omitted — no frontend duplication of routing logic).
  const handleFindSafeRoute = useCallback(() => {
    if (!selectedRiskZone) return;
    setError(null);
    setRescueRoute(null, "calculating");
    getRescueRoute(selectedRiskZone.lat, selectedRiskZone.lng)
      .then((result: RescueRouteResult) => storeResult(result, selectedRiskZone.name, "Safe zone"))
      .catch(() => {
        setError("Routing service unreachable — is the backend running on :8000?");
        setRescueRoute(null, "error");
      });
  }, [selectedRiskZone, setRescueRoute, storeResult]);

  // Alternative safe-zone option picked from the ranked list.
  const handleSelectOption = useCallback((opt: RescueRouteOption) => {
    if (!selectedRiskZone) return;
    setError(null);
    setRescueRoute(null, "calculating");
    getRescueRoute(selectedRiskZone.lat, selectedRiskZone.lng, opt.lat, opt.lng)
      .then((result: RescueRouteResult) => storeResult(result, selectedRiskZone.name, opt.name))
      .catch(() => {
        setError("Routing service unreachable — is the backend running on :8000?");
        setRescueRoute(null, "error");
      });
  }, [selectedRiskZone, setRescueRoute, storeResult]);

  // Map safe-zone click handoff: recalculate to the tapped safe zone.
  useEffect(() => {
    if (!safeZoneRequest || !selectedRiskZone) return;
    const req = safeZoneRequest;
    setSafeZoneRequest(null);
    setError(null);
    setRescueRoute(null, "calculating");
    getRescueRoute(selectedRiskZone.lat, selectedRiskZone.lng, req.lat, req.lng)
      .then((result: RescueRouteResult) => storeResult(result, selectedRiskZone.name, req.name))
      .catch(() => {
        setError("Routing service unreachable — is the backend running on :8000?");
        setRescueRoute(null, "error");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [safeZoneRequest]);

  const destName = route?.destination?.name ?? toZone?.name ?? "—";
  const why: string[] = (route?.explanation?.why ?? []).map((w: string) => w.replace(/\s*\(DEMO[^)]*\)/gi, "").replace(/demo/gi, ""));
  const tradeoffs: string[] = (route?.explanation?.tradeoffs ?? []).map((t: string) => t.replace(/\s*\(DEMO[^)]*\)/gi, "").replace(/demo/gi, ""));
  const roadsAvoided: any[] = route?.blocked_avoided ?? [];
  const segments: any[] = route?.segments ?? [];

  return (
    <div className="rounded-lg p-4" style={{ background: "#FFFFFF", border: "1px solid #E5E7EB" }}>
      <h3 className="text-[14px] font-bold text-gs-text mb-1">EMERGENCY ROUTING</h3>
      <p className="text-[11px] text-gs-text-secondary mb-3">
        Zone-to-zone rescue route on the OSM road network
      </p>

      {/* ── Risk zone → auto safe zone (map click → FIND SAFE ROUTE) ── */}
      {selectedRiskZone && (
        <div className="mb-3 rounded-lg p-2.5" style={{ background: "#EFF6FF", border: "1px solid #BFDBFE" }}>
          <div className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "#1D4ED8" }}>
            Selected risk zone
          </div>
          <div className="text-[12px] font-semibold text-gs-text">{selectedRiskZone.name}</div>
          <button
            onClick={handleFindSafeRoute}
            disabled={status === "calculating"}
            className="mt-2 w-full rounded-lg bg-risk-stable py-2 text-[12px] font-semibold text-white transition hover:opacity-90 disabled:opacity-50"
            style={{ background: "#1D4ED8" }}
          >
            {status === "calculating" ? <Spinner /> : "[ FIND SAFE ROUTE ]"}
          </button>
          <div className="mt-1 text-[10px] text-gs-text-secondary">
            Backend picks the nearest reachable safe zone over open roads.
          </div>
        </div>
      )}

      {/* ── Origin / destination selectors ── */}
      <div className="grid grid-cols-2 gap-2 mb-2">
        <label className="block">
          <span className="gs-label">From</span>
          <select
            value={fromId}
            onChange={(e) => setFromId(e.target.value)}
            className="mt-1 w-full rounded-md border border-gs-border bg-white px-2 py-1.5 text-[12px] text-gs-text"
          >
            {zones.map((z) => (
              <option key={z.id} value={z.id}>{z.name}</option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="gs-label">To</span>
          <select
            value={toId}
            onChange={(e) => setToId(e.target.value)}
            className="mt-1 w-full rounded-md border border-gs-border bg-white px-2 py-1.5 text-[12px] text-gs-text"
          >
            {zones.map((z) => (
              <option key={z.id} value={z.id}>{z.name}</option>
            ))}
          </select>
        </label>
      </div>

      {sameZone && (
        <p className="mb-2 text-[11px] text-risk-critical">Origin and destination must differ.</p>
      )}

      <button
        onClick={handleFindRoute}
        disabled={status === "calculating" || !fromZone || !toZone || sameZone}
        className="w-full rounded-lg bg-risk-stable py-2 text-[12px] font-semibold text-white transition hover:opacity-90 disabled:opacity-50"
      >
        {status === "calculating" ? <Spinner /> : "[ FIND LOWER-EXPOSURE ROUTE ]"}
      </button>

      {status === "calculating" && (
        <div className="mt-2 rounded-lg p-2 text-[11px] text-gs-text-secondary" style={{ background: "#F9FAFB" }}>
          <div className="font-bold text-gs-text">CALCULATING SAFE ROUTE…</div>
          <div>Analyzing road network · checking blocked segments · shortest path</div>
        </div>
      )}

      {status === "success" && route && (
        <div className="mt-3">
          <div className="rounded-lg p-3" style={{ background: "#F9FAFB", borderLeft: "3px solid #1D4ED8" }}>
            <div className="text-[10px] font-bold uppercase tracking-wider text-gs-text-secondary mb-1">
              Route found
            </div>
            <div className="text-[12px] text-gs-text">
              <span className="font-bold">● {fromZone?.name}</span>
              <span className="text-gs-text-secondary"> → </span>
              <span className="font-bold">◎ {destName}</span>
            </div>
            <div className="mt-2 grid grid-cols-3 gap-2 text-[11px]">
              <div>
                <span className="text-gs-text-secondary">Distance</span>
                <div className="font-bold text-gs-text">{route.distance_km} km</div>
              </div>
              <div>
                <span className="text-gs-text-secondary">ETA</span>
                <div className="font-bold text-gs-text">{fmtEta(route.eta_min)}</div>
              </div>
              <div>
                <span className="text-gs-text-secondary">Roads</span>
                <div className="font-bold text-gs-text">{route.road_count ?? segments.length}</div>
              </div>
            </div>
            <div className="mt-1 text-[10px] text-gs-text-secondary">
              {route.algorithm ?? "A*"} · {route.eta_basis ?? ""}
            </div>
            {route.exposure && (
              <div className="mt-1 text-[10px] italic text-gs-text-secondary">
                Distance-optimal route — exposure weighting off.
              </div>
            )}
          </div>

          {why.length > 0 && (
            <div className="mt-2 rounded-lg p-2 text-[11px] text-gs-text" style={{ background: "#F9FAFB" }}>
              <div className="gs-label mb-1">Why this route</div>
              <ul className="list-disc pl-4 space-y-0.5">
                {why.map((w, i) => <li key={i}>{w}</li>)}
                {tradeoffs.map((t, i) => <li key={`t${i}`}>{t}</li>)}
              </ul>
            </div>
          )}

          <button
            onClick={() => setShowRoads((s) => !s)}
            className="mt-2 w-full rounded-lg px-3 py-1.5 text-[11px] font-semibold text-gs-text transition hover:bg-gray-100"
            style={{ border: "1px solid #E5E7EB" }}
          >
            {showRoads ? "▾ Hide route details" : "▸ Route details"}
          </button>
          {showRoads && (
            <div className="mt-1 max-h-48 overflow-y-auto rounded-lg p-2 text-[11px]" style={{ border: "1px solid #E5E7EB" }}>
              {segments.map((s: any, i: number) => (
                <div key={i} className="flex items-center justify-between gap-2 border-b border-gray-100 py-1 last:border-0">
                  <span className="text-gs-text">
                    <span className="font-mono text-gs-text-secondary">{String(i + 1).padStart(2, "0")}</span>{" "}
                    {s.name || `Road ${s.road_id}`}
                  </span>
                  <span className="shrink-0 tabular-nums text-gs-text-secondary">
                    {(s.length_m / 1000).toFixed(1)} km · {s.status}
                  </span>
                </div>
              ))}
              {roadsAvoided.length > 0 && (
                <div className="mt-2">
                  <div className="gs-label mb-1">Roads avoided</div>
                  {roadsAvoided.map((b: any, i: number) => (
                    <div key={i} className="text-risk-critical">
                      ✕ {b.name || `Road ${b.road_id}`} — BLOCKED{b.reason ? ` · ${b.reason}` : ""}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── Journey controls ── */}
          <div className="mt-2 flex gap-2">
            {journeyPhase === "running" ? (
              <button
                onClick={() => setJourneyPhase("paused")}
                className="flex-1 rounded-lg bg-forest py-2 text-[12px] font-semibold text-white transition hover:opacity-90"
              >
                ❚❚ PAUSE
              </button>
            ) : journeyPhase === "paused" ? (
              <button
                onClick={() => setJourneyPhase("running")}
                className="flex-1 rounded-lg bg-risk-stable py-2 text-[12px] font-semibold text-white transition hover:opacity-90"
              >
                ▶ RESUME
              </button>
            ) : (
              <button
                onClick={() => { resetJourney(); setJourneyPhase("running"); }}
                className="flex-1 rounded-lg bg-risk-stable py-2 text-[12px] font-semibold text-white transition hover:opacity-90"
              >
                ▶ {journeyPhase === "done" ? "REPLAY JOURNEY" : "START JOURNEY"}
              </button>
            )}
            <button
              onClick={() => resetJourney()}
              className="rounded-lg px-3 py-2 text-[12px] font-semibold text-gs-text transition hover:bg-gray-100"
              style={{ border: "1px solid #E5E7EB" }}
            >
              RESET
            </button>
            <button
              onClick={() => clearRescueRoute()}
              className="rounded-lg px-3 py-2 text-[12px] font-semibold text-gs-text transition hover:bg-gray-100"
              style={{ border: "1px solid #E5E7EB" }}
            >
              CLEAR
            </button>
          </div>

          {/* ── Other reachable safe zones (backend-ranked) ── */}
          {(route.options ?? []).length > 0 && (
            <div className="mt-2 rounded-lg p-2 text-[11px]" style={{ background: "#F9FAFB", border: "1px solid #E5E7EB" }}>
              <div className="gs-label mb-1">Other reachable options</div>
              {(route.options ?? []).map((opt) => (
                <button
                  key={opt.id}
                  onClick={() => handleSelectOption(opt)}
                  className="mb-1 flex w-full items-center justify-between gap-2 rounded-md bg-white px-2 py-1.5 text-left transition hover:bg-blue-50 disabled:opacity-50"
                  style={{ border: "1px solid #E5E7EB" }}
                >
                  <span className="font-semibold text-gs-text">◎ {opt.name}</span>
                  <span className="shrink-0 tabular-nums text-gs-text-secondary">
                    {opt.distance_km} km · ~{opt.eta_min} min
                  </span>
                </button>
              ))}
              <div className="mt-1 text-[10px] italic text-gs-text-secondary">
                Tap an option to redraw the blue route to that safe zone.
              </div>
            </div>
          )}
        </div>
      )}

      {status === "unavailable" && (
        <div className="mt-2 rounded-lg p-3 text-[11px]" style={{ background: "#FEF2F2", color: "#991B1B" }}>
          <div className="font-bold mb-1">ROUTE UNAVAILABLE</div>
          <div>{route?.explanation?.why?.[0] ?? "No connected road-network path was found between these locations using the available OSM network."}</div>
          <div className="mt-1 italic">No route has been drawn.</div>
        </div>
      )}

      {(status === "error" || error) && (
        <div className="mt-2 rounded-lg p-2 text-[11px]" style={{ background: "#FEF2F2", color: "#991B1B" }}>
          <span className="font-bold">ROUTING SERVICE UNAVAILABLE. </span>
          {error ?? "Unable to calculate the route. Please try again."}
        </div>
      )}

      <p className="mt-2 text-[9px] italic text-gs-text-secondary">
        Advisory indicator only — uncalibrated, not a probability.
      </p>
    </div>
  );
}

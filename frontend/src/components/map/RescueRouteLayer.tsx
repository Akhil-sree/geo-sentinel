import { useEffect, useRef } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import { useUIStore } from "../../store/uiStore";
import type { RescueRouteResult } from "../../api/dashboard";

const ROUTE_STYLE = {
  color: "#1D4ED8",
  weight: 5,
  opacity: 0.95,
  lineCap: "round" as const,
  lineJoin: "round" as const,
};

const GLOW_STYLE = {
  color: "#3B82F6",
  weight: 10,
  opacity: 0.18,
  lineCap: "round" as const,
  lineJoin: "round" as const,
};

const JOURNEY_TICK_MS = 120;

function createArrowIcon(angle: number): L.DivIcon {
  const size = 10;
  return L.divIcon({
    className: "rescue-route-arrow",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    html: `<div style="
      width:0;height:0;
      border-left:${size / 2}px solid transparent;
      border-right:${size / 2}px solid transparent;
      border-bottom:${size}px solid #1D4ED8;
      transform:rotate(${angle}deg);
      opacity:0.9;
    "></div>`,
  });
}

function computeAngle(from: [number, number], to: [number, number]): number {
  const dx = to[1] - from[1];
  const dy = to[0] - from[0];
  return (Math.atan2(dx, -dy) * 180) / Math.PI;
}

function startIcon(): L.DivIcon {
  return L.divIcon({
    className: "rescue-origin-marker",
    iconSize: [18, 18],
    iconAnchor: [9, 9],
    html: `<div style="width:18px;height:18px;border-radius:50%;background:#DC2626;border:3px solid #FFFFFF;box-shadow:0 1px 4px rgba(0,0,0,0.4)"></div>`,
  });
}

function destIcon(): L.DivIcon {
  return L.divIcon({
    className: "rescue-dest-marker",
    iconSize: [22, 22],
    iconAnchor: [11, 11],
    html: `<div style="width:22px;height:22px;border-radius:50%;background:#1D4ED8;border:3px solid #FFFFFF;box-shadow:0 0 0 5px rgba(29,78,216,0.25),0 1px 4px rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;color:#fff;font-size:11px;font-weight:800;">◎</div>`,
  });
}

function unitIcon(): L.DivIcon {
  return L.divIcon({
    className: "rescue-unit-marker",
    iconSize: [16, 16],
    iconAnchor: [8, 8],
    html: `<div style="width:16px;height:16px;border-radius:50%;background:#F59E0B;border:3px solid #FFFFFF;box-shadow:0 1px 5px rgba(0,0,0,0.5)"></div>`,
  });
}

/** Canonical API → Leaflet conversion (§27 regression anchor).
 *  Format change ONLY ([lng,lat] → [lat,lng]); values, order and count
 *  are preserved verbatim — never re-routed, interpolated or simplified. */
export function routeCoordsToLatLngs(coords: number[][]): [number, number][] {
  return coords.map((c) => [c[1], c[0]]);
}

/** Single map-input contract: backend `route_geometry` ([lat,lng]) wins;
 *  legacy `geometry.coordinates` ([lng,lat]) is converted. Returns [] when
 *  the backend sent no drawable path — the layer then draws nothing. */
export function routeLatLngs(route: RescueRouteResult | null | undefined): [number, number][] {
  if (!route) return [];
  if (route.route_geometry && route.route_geometry.length >= 2) {
    return route.route_geometry.map((c) => [c[0], c[1]]);
  }
  const coords = route.geometry?.coordinates;
  if (!coords || coords.length < 2) return [];
  return routeCoordsToLatLngs(coords);
}

interface RescueRouteLayerProps {
  visible: boolean;
}

/** Renders the EXACT backend route geometry — no transformation besides
 *  [lng,lat] → [lat,lng] for Leaflet. Same store object as the panel. */
export default function RescueRouteLayer({ visible }: RescueRouteLayerProps) {
  const map = useMap();
  const route = useUIStore((s) => s.rescueRoute);
  const status = useUIStore((s) => s.rescueStatus);
  const journeyPhase = useUIStore((s) => s.journeyPhase);
  const journeyStep = useUIStore((s) => s.journeyStep);
  const setJourneyStep = useUIStore((s) => s.setJourneyStep);
  const setJourneyPhase = useUIStore((s) => s.setJourneyPhase);

  const layerRef = useRef<L.LayerGroup | null>(null);
  const unitRef = useRef<L.Marker | null>(null);
  const routeKeyRef = useRef<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearAll = () => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    if (unitRef.current) { map.removeLayer(unitRef.current); unitRef.current = null; }
    if (layerRef.current) { map.removeLayer(layerRef.current); layerRef.current = null; }
  };

  // ── Render / clear route. Stale geometry is always removed first. ──
  useEffect(() => {
    clearAll();
    routeKeyRef.current = null;
    if (!visible || status !== "success" || !route?.route_available) return;
    // Exact backend coordinates — route_geometry preferred, geometry fallback.
    const latLngs = routeLatLngs(route);
    if (latLngs.length < 2) return;

    const group = L.layerGroup();
    L.polyline(latLngs, GLOW_STYLE).addTo(group);
    const line = L.polyline(latLngs, ROUTE_STYLE);
    line.bindTooltip(
      `<div style="font-size:12px;font-weight:700">Rescue route</div>
       <div style="font-size:11px">${route.distance_km} km · ~${route.eta_min ?? "—"} min · ${route.road_count ?? route.segments?.length ?? 0} roads</div>`,
      { sticky: true, className: "road-tooltip" }
    );
    line.addTo(group);

    const arrowInterval = Math.max(1, Math.floor(latLngs.length / 15));
    for (let i = 0; i < latLngs.length - 1; i += arrowInterval) {
      L.marker(latLngs[i], {
        icon: createArrowIcon(computeAngle(latLngs[i], latLngs[Math.min(i + 1, latLngs.length - 1)])),
        interactive: false,
      }).addTo(group);
    }

    const originName = route.originName ?? "Origin";
    const destName = route.destName ?? route.destination?.name ?? "Destination";
    L.marker(latLngs[0], { icon: startIcon() })
      .bindTooltip(
        `<div style="font-size:11px;font-weight:700">START</div><div style="font-size:12px">${originName}</div>`,
        { direction: "top", offset: [0, -12], className: "road-tooltip" }
      )
      .addTo(group);
    L.marker(latLngs[latLngs.length - 1], { icon: destIcon() })
      .bindTooltip(
        `<div style="font-size:11px;font-weight:700;color:#1D4ED8">SAFE DESTINATION</div><div style="font-size:12px">${destName}</div>`,
        { direction: "top", offset: [0, -14], className: "road-tooltip" }
      )
      .addTo(group);

    group.addTo(map);
    layerRef.current = group;
    const key = JSON.stringify([latLngs[0], latLngs[latLngs.length - 1], latLngs.length]);
    routeKeyRef.current = key;

    // Auto-fit once per new route (§13)
    map.fitBounds(L.latLngBounds(latLngs), { padding: [60, 60] });

    return () => { clearAll(); routeKeyRef.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible, status, route, map]);

  // ── Journey animation: advances along the SAME geometry ──
  useEffect(() => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    if (journeyPhase !== "running") return;
    const latLngs = routeLatLngs(route);
    if (latLngs.length < 2) return;
    if (journeyStep === 0) {
      map.fitBounds(L.latLngBounds(latLngs), { padding: [60, 60] });
    }
    timerRef.current = setInterval(() => {
      const next = useUIStore.getState().journeyStep + 1;
      if (next >= latLngs.length) {
        if (timerRef.current) clearInterval(timerRef.current);
        timerRef.current = null;
        useUIStore.getState().setJourneyPhase("done");
        return;
      }
      useUIStore.getState().setJourneyStep(next);
    }, JOURNEY_TICK_MS);
    return () => {
      if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [journeyPhase, route, map]);

  // ── Journey unit marker follows geometry ──
  useEffect(() => {
    if (unitRef.current) { map.removeLayer(unitRef.current); unitRef.current = null; }
    const latLngs = routeLatLngs(route);
    if (latLngs.length < 2) return;
    if (journeyPhase !== "running" && journeyPhase !== "paused" && journeyPhase !== "done") return;
    const idx = Math.min(journeyStep, latLngs.length - 1);
    const marker = L.marker([latLngs[idx][0], latLngs[idx][1]], { icon: unitIcon(), interactive: false });
    marker.addTo(map);
    unitRef.current = marker;
    return () => {
      if (unitRef.current) { map.removeLayer(unitRef.current); unitRef.current = null; }
    };
  }, [journeyStep, journeyPhase, route, map]);

  // setJourneyStep/setJourneyPhase referenced via getState in timer; keep lints quiet
  void setJourneyStep;
  void setJourneyPhase;

  return null;
}

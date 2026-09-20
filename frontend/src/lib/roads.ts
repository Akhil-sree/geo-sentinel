/** Road GIS helpers — real OSM geometry support. */

export interface RoadSegmentPoint {
  id: string | number;
  name: string;
  status: string;
  road_type?: string;
  length_km?: number;
  latitude: number;
  longitude: number;
}

export interface SnapResult {
  original: { lat: number; lng: number };
  snapped: { lat: number; lng: number };
  segment_id: string | number;
  segment_name: string;
  road_distance_m: number;
}

export function haversineKm(aLat: number, aLng: number, bLat: number, bLng: number): number {
  const R = 6371;
  const dLat = ((bLat - aLat) * Math.PI) / 180;
  const dLng = ((bLng - aLng) * Math.PI) / 180;
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((aLat * Math.PI) / 180) *
      Math.cos((bLat * Math.PI) / 180) *
      Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(s));
}

export function haversineM(aLat: number, aLng: number, bLat: number, bLng: number): number {
  return haversineKm(aLat, aLng, bLat, bLng) * 1000;
}

function validCoord(lat: number, lng: number): boolean {
  return (
    typeof lat === "number" &&
    typeof lng === "number" &&
    Number.isFinite(lat) &&
    Number.isFinite(lng) &&
    lat >= -90 &&
    lat <= 90 &&
    lng >= -180 &&
    lng <= 180
  );
}

/** Distance from point to line segment in meters (geodesic). */
export function pointToSegmentDistanceM(
  px: number, py: number,
  ax: number, ay: number,
  bx: number, by: number,
): number {
  const dx = bx - ax;
  const dy = by - ay;
  if (dx === 0 && dy === 0) return haversineM(py, px, ay, ax);
  const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)));
  const projX = ax + t * dx;
  const projY = ay + t * dy;
  return haversineM(py, px, projY, projX);
}

/** Snap a location to the nearest road segment midpoint (legacy graph). */
export function snapToRoad(
  lat: number,
  lng: number,
  segments: RoadSegmentPoint[],
): SnapResult | null {
  if (!validCoord(lat, lng) || !Array.isArray(segments) || segments.length === 0)
    return null;
  let best: RoadSegmentPoint | null = null;
  let bestKm = Infinity;
  for (const s of segments) {
    if (!s || !validCoord(s.latitude, s.longitude)) continue;
    const d = haversineKm(lat, lng, s.latitude, s.longitude);
    if (d < bestKm) {
      bestKm = d;
      best = s;
    }
  }
  if (!best) return null;
  return {
    original: { lat, lng },
    snapped: { lat: best.latitude, lng: best.longitude },
    segment_id: best.id,
    segment_name: best.name,
    road_distance_m: Math.round(bestKm * 1000),
  };
}

/** Marker radius by road class. */
export function roadClassRadius(roadType: string | undefined): number {
  switch ((roadType || "").toLowerCase()) {
    case "national":
      return 7;
    case "state":
      return 6;
    case "district":
      return 5;
    default:
      return 4;
  }
}

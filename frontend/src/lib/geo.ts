/** Zone geometry helpers.
 * Real deployments load authoritative boundary polygons; the fallback snaps
 * each zone centroid to a hexagonal cell (situational-awareness grid look).
 */

const R_KM = 4; // hex radius in km — tune 3–6 until hexes tile nicely

export function zonePolygonCoords(zone: { lat: number; lng: number }): [number, number][] {
  const R = R_KM / 111; // degrees latitude
  return Array.from({ length: 6 }, (_, i): [number, number] => {
    const a = (Math.PI / 3) * i + Math.PI / 6; // flat-top hexagons
    return [
      zone.lat + R * Math.sin(a),
      zone.lng + (R * Math.cos(a)) / Math.cos((zone.lat * Math.PI) / 180),
    ];
  });
}

/** Generate deterministic hotspot coordinates within a zone's hexagonal boundary.
 *  Uses a simple hash of zoneId for reproducible placement.
 *  Count scales with severity: LOW=1, MODERATE=2, HIGH=3, VERY_HIGH=4. */
export function generateHotspotCoords(
  zone: { lat: number; lng: number; id: string },
  severity: string,
): { lat: number; lng: number }[] {
  const countMap: Record<string, number> = {
    LOW: 1,
    MODERATE: 2,
    HIGH: 3,
    VERY_HIGH: 4,
  };
  const count = countMap[severity] ?? 2;
  const R = R_KM / 111;

  // Simple deterministic hash from zone id
  let hash = 0;
  for (let i = 0; i < zone.id.length; i++) {
    hash = ((hash << 5) - hash + zone.id.charCodeAt(i)) | 0;
  }

  const points: { lat: number; lng: number }[] = [];
  for (let i = 0; i < count; i++) {
    // Pseudo-random angle and radius using hash + index
    const seed = ((hash + i * 7919) >>> 0) / 4294967296;
    const seed2 = (((hash << 3) + i * 104729) >>> 0) / 4294967296;
    const angle = seed * Math.PI * 2;
    const dist = (0.15 + seed2 * 0.55) * R; // 15-70% of hex radius
    points.push({
      lat: zone.lat + Math.sin(angle) * dist,
      lng: zone.lng + (Math.cos(angle) * dist) / Math.cos((zone.lat * Math.PI) / 180),
    });
  }
  return points;
}


export const haversineKm = (
  a: { lat: number; lng: number }, b: { lat: number; lng: number }
) => {
  const R = 6371, toR = Math.PI / 180;
  const dLat = (b.lat - a.lat) * toR, dLng = (b.lng - a.lng) * toR;
  const h = Math.sin(dLat / 2) ** 2 +
    Math.cos(a.lat * toR) * Math.cos(b.lat * toR) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
};

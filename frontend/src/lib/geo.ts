/** Demo zones have a point + no real boundary. We generate a rough hexagonal
 *  footprint around each centroid sized by population, clearly labeled as
 *  DEMO geometry. Production: replace with real GSI zone polygons (GeoJSON). */
/** Zone geometry helpers.
 * Real deployments load authoritative boundary polygons; the demo snaps
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


export const haversineKm = (
  a: { lat: number; lng: number }, b: { lat: number; lng: number }
) => {
  const R = 6371, toR = Math.PI / 180;
  const dLat = (b.lat - a.lat) * toR, dLng = (b.lng - a.lng) * toR;
  const h = Math.sin(dLat / 2) ** 2 +
    Math.cos(a.lat * toR) * Math.cos(b.lat * toR) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
};

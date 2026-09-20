import { useEffect, useRef, useState } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import { getRoadsGeoJSON, findNearestRoad, type RoadFeature, type NearestRoadResult } from "../../api/dashboard";
import type { RoadCategoryFilters } from "./LayerControl";

const CATEGORY_STYLES: Record<string, { color: string; weight: number; opacity: number; dashArray?: string }> = {
  major:    { color: "#6B7B6E", weight: 3.5, opacity: 0.7 },
  secondary:{ color: "#8A9A8D", weight: 2.5, opacity: 0.6 },
  local:    { color: "#A0ADA3", weight: 1.5, opacity: 0.45 },
  minor:    { color: "#B5C0B8", weight: 1,   opacity: 0.35, dashArray: "4 3" },
};

const HIGHLIGHT_STYLE = { color: "#1A3C2E", weight: 5, opacity: 1 };

interface RoadNetworkLayerProps {
  selectedRoadId?: number | null;
  onRoadSelect?: (road: RoadFeature | null) => void;
  roadFilters?: RoadCategoryFilters;
  blockedRoadIds?: Set<number>;
}

export default function RoadNetworkLayer({
  selectedRoadId,
  onRoadSelect,
  roadFilters,
  blockedRoadIds,
}: RoadNetworkLayerProps) {
  const map = useMap();
  const layerGroupRef = useRef<L.LayerGroup | null>(null);
  const selectedRef = useRef<L.Polyline | null>(null);
  const [roadData, setRoadData] = useState<RoadFeature[] | null>(null);

  // Load road GeoJSON once
  useEffect(() => {
    let cancelled = false;
    getRoadsGeoJSON()
      .then((data) => {
        if (!cancelled && data.features) {
          setRoadData(data.features);
        }
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  // Render roads on the map
  useEffect(() => {
    if (!roadData || roadData.length === 0) return;

    if (layerGroupRef.current) {
      map.removeLayer(layerGroupRef.current);
    }

    const group = L.layerGroup();
    const activeCats = new Set(
      Object.entries(roadFilters ?? { major: true, secondary: true, local: true, minor: true })
        .filter(([, v]) => v)
        .map(([k]) => k)
    );

    for (const feature of roadData) {
      const coords = feature.geometry.coordinates;
      const cat = feature.properties.category || "local";
      if (!activeCats.has(cat)) continue;
      const style = CATEGORY_STYLES[cat] || CATEGORY_STYLES.local;

      // Override style for blocked/damaged roads
      const roadId = feature.properties.road_id;
      const isBlocked = blockedRoadIds?.has(roadId) ?? false;
      const effectiveStyle = isBlocked
        ? { color: "#DC2626", weight: 3, opacity: 0.8, dashArray: "8 4" }
        : style;

      let latLngs: L.LatLngExpression[];
      if (feature.geometry.type === "MultiLineString") {
        // Draw each segment separately
        for (const ring of coords) {
          latLngs = (ring as number[][]).map((c) => [c[1], c[0]] as [number, number]);
          const line = L.polyline(latLngs, {
            color: effectiveStyle.color,
            weight: effectiveStyle.weight,
            opacity: effectiveStyle.opacity,
            dashArray: effectiveStyle.dashArray,
            lineCap: "round",
            lineJoin: "round",
            className: `road-line road-${cat}`,
          });
          (line as any).__roadId = feature.properties.road_id;
          (line as any).__roadFeature = feature;
          line.bindTooltip(
            `<div style="font-size:12px;font-weight:600">${feature.properties.name || "Unnamed road"}</div>
             <div style="font-size:11px;color:#666">${feature.properties.highway}${feature.properties.ref ? " · " + feature.properties.ref : ""}${isBlocked ? ' · <span style="color:#DC2626;font-weight:700">BLOCKED</span><div style="font-size:10px">landslide · avoided by rescue routing</div>' : ""}</div>`,
            { sticky: true, className: "road-tooltip" }
          );
          line.on("click", () => onRoadSelect?.(feature));
          line.addTo(group);
        }
      } else {
        latLngs = (coords as number[][]).map((c) => [c[1], c[0]] as [number, number]);
        const line = L.polyline(latLngs, {
          color: effectiveStyle.color,
          weight: effectiveStyle.weight,
          opacity: effectiveStyle.opacity,
          dashArray: effectiveStyle.dashArray,
          lineCap: "round",
          lineJoin: "round",
          className: `road-line road-${cat}`,
        });
        (line as any).__roadId = feature.properties.road_id;
        (line as any).__roadFeature = feature;
        line.bindTooltip(
          `<div style="font-size:12px;font-weight:600">${feature.properties.name || "Unnamed road"}</div>
           <div style="font-size:11px;color:#666">${feature.properties.highway}${feature.properties.ref ? " · " + feature.properties.ref : ""}${isBlocked ? ' · <span style="color:#DC2626;font-weight:700">BLOCKED</span><div style="font-size:10px">landslide · avoided by rescue routing</div>' : ""}</div>`,
          { sticky: true, className: "road-tooltip" }
        );
        line.on("click", () => onRoadSelect?.(feature));
        line.addTo(group);
      }
    }

    group.addTo(map);
    layerGroupRef.current = group;

    return () => {
      if (layerGroupRef.current) {
        map.removeLayer(layerGroupRef.current);
        layerGroupRef.current = null;
      }
    };
  }, [roadData, map, onRoadSelect, roadFilters, blockedRoadIds]);

  // Highlight selected road
  useEffect(() => {
    if (!layerGroupRef.current) return;

    // Remove previous highlight
    if (selectedRef.current) {
      map.removeLayer(selectedRef.current);
      selectedRef.current = null;
    }

    if (selectedRoadId == null || !roadData) return;

    const feature = roadData.find((f) => f.properties.road_id === selectedRoadId);
    if (!feature) return;

    const coords = feature.geometry.coordinates;
    let latLngs: L.LatLngExpression[];

    if (feature.geometry.type === "MultiLineString") {
      for (const ring of coords) {
        latLngs = (ring as number[][]).map((c) => [c[1], c[0]] as [number, number]);
        const highlight = L.polyline(latLngs, {
          ...HIGHLIGHT_STYLE,
          lineCap: "round",
          lineJoin: "round",
        });
        highlight.addTo(map);
        selectedRef.current = highlight;
      }
    } else {
      latLngs = (coords as number[][]).map((c) => [c[1], c[0]] as [number, number]);
      const highlight = L.polyline(latLngs, {
        ...HIGHLIGHT_STYLE,
        lineCap: "round",
        lineJoin: "round",
      });
      highlight.addTo(map);
      selectedRef.current = highlight;
    }
  }, [selectedRoadId, roadData, map]);

  return null;
}

/** Hook: find nearest real road to a lat/lng point */
export function useNearestRoad(lat: number | null, lng: number | null) {
  const [result, setResult] = useState<NearestRoadResult | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (lat == null || lng == null || !Number.isFinite(lat) || !Number.isFinite(lng)) {
      setResult(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    findNearestRoad(lat, lng)
      .then((r) => { if (!cancelled) setResult(r); })
      .catch(() => { if (!cancelled) setResult(null); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [lat, lng]);

  return { nearestRoad: result, loading };
}

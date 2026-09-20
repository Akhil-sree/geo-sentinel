import { useEffect, useRef, useState } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import { getSafeZones, type SafeZone } from "../../api/dashboard";
import { useUIStore } from "../../store/uiStore";

const SAFE_ZONE_STYLE = {
  color: "#2563EB",
  weight: 2,
  fillColor: "#3B82F6",
  fillOpacity: 0.15,
  opacity: 0.6,
};

const SAFE_ZONE_HOVER_STYLE = {
  weight: 3,
  fillOpacity: 0.25,
  opacity: 0.9,
};

const SAFE_ZONE_TARGET_STYLE = {
  color: "#1D4ED8",
  weight: 3,
  fillColor: "#3B82F6",
  fillOpacity: 0.3,
  opacity: 1,
};

export default function SafeZoneLayer({ visible }: { visible: boolean }) {
  const map = useMap();
  const layerRef = useRef<L.LayerGroup | null>(null);
  const [zones, setZones] = useState<SafeZone[]>([]);
  const setSafeZoneRequest = useUIStore((s) => s.setSafeZoneRequest);
  const selectedZoneId = useUIStore((s) => s.selectedZoneId);
  const destId = useUIStore((s) => s.rescueRoute?.destination?.id);

  useEffect(() => {
    let cancelled = false;
    getSafeZones()
      .then((data) => { if (!cancelled) setZones(data.safe_zones || []); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (layerRef.current) {
      map.removeLayer(layerRef.current);
      layerRef.current = null;
    }
    if (!visible || zones.length === 0) return;

    const group = L.layerGroup();

    for (const zone of zones) {
      if (!Number.isFinite(zone.lat) || !Number.isFinite(zone.lng)) continue;
      const isTarget = destId != null && destId === zone.id;

      // ponytail: 800m radius circle (meters) + center dot; was circleMarker radius:800px
      const area = L.circle([zone.lat, zone.lng], {
        radius: 800,
        ...(isTarget ? SAFE_ZONE_TARGET_STYLE : SAFE_ZONE_STYLE),
      });

      area.bindTooltip(
        `<div style="font-size:12px;font-weight:600">${zone.name}</div>
         <div style="font-size:10px;color:#666">${zone.type} · ${zone.district}</div>
         <div style="font-size:9px;color:#1D4ED8;font-weight:700;margin-top:2px">Safe zone — tap to route here</div>`,
        { sticky: true, className: "road-tooltip" }
      );

      if (!isTarget) {
        area.on("mouseover", function (this: L.Circle) {
          this.setStyle(SAFE_ZONE_HOVER_STYLE);
        });
        area.on("mouseout", function (this: L.Circle) {
          this.setStyle(SAFE_ZONE_STYLE);
        });
      }

      // Tap a safe zone to recalculate the rescue route to it
      // (only meaningful once a risk zone is selected as origin).
      area.on("click", () => {
        if (!selectedZoneId) return;
        setSafeZoneRequest({ safeId: zone.id, lat: zone.lat, lng: zone.lng, name: zone.name });
      });

      area.addTo(group);

      const dot = L.circleMarker([zone.lat, zone.lng], {
        radius: isTarget ? 8 : 6,
        color: "#1D4ED8",
        weight: 2,
        fillColor: "#1D4ED8",
        fillOpacity: 0.9,
        opacity: 0.9,
      });
      dot.on("click", () => {
        if (!selectedZoneId) return;
        setSafeZoneRequest({ safeId: zone.id, lat: zone.lat, lng: zone.lng, name: zone.name });
      });
      dot.addTo(group);
    }

    group.addTo(map);
    layerRef.current = group;

    return () => {
      if (layerRef.current) {
        map.removeLayer(layerRef.current);
        layerRef.current = null;
      }
    };
  }, [visible, zones, map, selectedZoneId, destId, setSafeZoneRequest]);

  return null;
}

import { Marker } from "react-leaflet";
import L from "leaflet";
import { useUIStore } from "../../store/uiStore";
import type { ZoneRisk } from "../../types/risk";

const SEV_COLOR: Record<string, string> = {
  VERY_HIGH: "#B4232B",
  HIGH: "#E76016",
  MODERATE: "#D19217",
  LOW: "#2563EB",
};

// GIS-style dots: small core, thin halo; animated ring ONLY when selected.
const SIZE_MAP: Record<string, { core: number; halo: number }> = {
  VERY_HIGH: { core: 5, halo: 9 },
  HIGH: { core: 4.5, halo: 8 },
  MODERATE: { core: 4, halo: 7 },
  LOW: { core: 3.5, halo: 6.5 },
};

function makeDotIcon(severity: string, selected: boolean) {
  const color = SEV_COLOR[severity] ?? SEV_COLOR.LOW;
  const { core, halo } = SIZE_MAP[severity] ?? SIZE_MAP.LOW;
  const ring = selected ? halo + 7 : halo;
  const size = (ring + 3) * 2;
  const cx = size / 2;

  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
      ${selected ? `<circle cx="${cx}" cy="${cx}" r="${ring}" fill="none" stroke="${color}" stroke-width="1.5" opacity="0.9"/>` : ""}
      <circle cx="${cx}" cy="${cx}" r="${halo}" fill="${color}" opacity="0.22"/>
      <circle cx="${cx}" cy="${cx}" r="${core}" fill="${color}" stroke="#fff" stroke-width="1.5"/>
    </svg>
  `.trim();

  return L.divIcon({
    className: "hotspot-triangle-icon",
    html: svg,
    iconSize: [size, size],
    iconAnchor: [cx, cx],
    popupAnchor: [0, -cx],
  });
}

interface HotspotMarkerProps {
  lat: number;
  lng: number;
  risk: ZoneRisk;
  index: number;
  selected?: boolean;
  onHover: (
    risk: ZoneRisk | null,
    position: { x: number; y: number } | null,
    markerIndex: number,
  ) => void;
}

export default function HotspotMarker({ lat, lng, risk, index, selected = false, onHover }: HotspotMarkerProps) {
  const selectZone = useUIStore((s) => s.selectZone);
  const icon = makeDotIcon(risk.severity, selected);

  return (
    <Marker
      position={[lat, lng]}
      icon={icon}
      eventHandlers={{
        click: () => selectZone(risk.zone_id),
        mouseover: (e) => {
          const map = e.target._map;
          if (!map) return;
          const container = map.getContainer();
          const rect = container.getBoundingClientRect();
          const point = map.latLngToContainerPoint(e.latlng);
          onHover(risk, { x: rect.left + point.x, y: rect.top + point.y }, index);
        },
        mouseout: () => onHover(null, null, index),
      }}
    />
  );
}

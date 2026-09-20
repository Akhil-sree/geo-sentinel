import { Marker, Popup } from "react-leaflet";
import L from "leaflet";
import type { ThreatZone } from "./RiskMap";

const COLORS: Record<string, string> = {
  critical: "#D62828",
  high: "#E85D04",
  moderate: "#F2B705",
  low: "#20A464",
};

const AURA_COLORS: Record<string, string> = {
  critical: "rgba(214,40,40,0.12)",
  high: "rgba(232,93,4,0.10)",
  moderate: "rgba(242,183,5,0.08)",
  low: "rgba(32,164,100,0.06)",
};

// Compact GIS markers: small core + faint halo; pulse ring ONLY when
// selected (previously every marker pulsed — visual noise).
const SIZES: Record<string, { core: number; aura: number }> = {
  critical: { core: 11, aura: 26 },
  high: { core: 10, aura: 23 },
  moderate: { core: 9, aura: 20 },
  low: { core: 8, aura: 17 },
};

const SPEEDS: Record<string, string> = {
  critical: "2.4s",
  high: "3.2s",
  moderate: "4s",
  low: "6s",
};

const ICON_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 12 12" fill="none" stroke="rgba(255,255,255,0.7)" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 9.5L5 3.5L7.5 7L9 5.5L10.5 9.5"/><path d="M5 3.5L6.5 1.5"/></svg>`;

function makeThreatIcon(zone: ThreatZone, isSelected: boolean) {
  const color = COLORS[zone.risk];
  const auraColor = AURA_COLORS[zone.risk];
  const { core, aura } = SIZES[zone.risk];
  const speed = SPEEDS[zone.risk];
  const selectedBoost = isSelected ? 6 : 0;
  const total = aura * 2 + 12;
  const cx = total / 2;
  const cy = total / 2;
  const coreSize = core + selectedBoost;
  const iconSize = Math.max(6, coreSize * 0.45);

  const html = `
    <div style="position:relative;width:${total}px;height:${total}px;pointer-events:none;">
      <!-- Layer 1: Soft thermal aura -->
      <div style="
        position:absolute;
        left:${cx - aura / 2}px;top:${cy - aura / 2}px;
        width:${aura}px;height:${aura}px;border-radius:50%;
        background:radial-gradient(circle, ${auraColor} 0%, transparent 70%);
        opacity:${isSelected ? 1 : 0.8};
        transition:opacity 0.3s;
      "></div>

      <!-- Layer 2: pulse ring on the SELECTED marker only -->
      ${isSelected ? `
      <div class="hs-pulse" style="
        position:absolute;
        left:${cx - coreSize / 2}px;top:${cy - coreSize / 2}px;
        width:${coreSize}px;height:${coreSize}px;border-radius:50%;
        border:1px solid ${color};
        opacity:0;
        animation:hs-pulse ${speed} ease-out infinite;
      "></div>` : ""}

      <!-- Layer 3: Colored core -->
      <div style="
        position:absolute;
        left:${cx - coreSize / 2}px;top:${cy - coreSize / 2}px;
        width:${coreSize}px;height:${coreSize}px;border-radius:50%;
        background:radial-gradient(circle at 40% 35%, ${color}ee, ${color}cc 60%, ${color}99 100%);
        box-shadow:0 1px 4px rgba(0,0,0,0.3), inset 0 1px 1px rgba(255,255,255,0.1);
        display:flex;align-items:center;justify-content:center;
        z-index:2;
        transition:transform 0.2s, box-shadow 0.2s;
        transform:scale(${isSelected ? 1.1 : 1});
        box-shadow:0 1px 4px rgba(0,0,0,0.3), inset 0 1px 1px rgba(255,255,255,0.1)${isSelected ? `, 0 0 0 2px ${color}55` : ""};
      ">
        <!-- Landslide icon -->
        <div style="width:${iconSize}px;height:${iconSize}px;display:flex;align-items:center;justify-content:center;">
          ${ICON_SVG}
        </div>
      </div>

      ${isSelected ? `
      <!-- Selected: subtle secondary ring -->
      <div style="
        position:absolute;
        left:${cx - coreSize / 2 - 5}px;top:${cy - coreSize / 2 - 5}px;
        width:${coreSize + 10}px;height:${coreSize + 10}px;border-radius:50%;
        border:1.5px solid ${color}44;
        z-index:1;
      "></div>` : ""}
    </div>
  `;

  return L.divIcon({
    className: "hs-marker-icon",
    html,
    iconSize: [total, total],
    iconAnchor: [cx, cy],
    popupAnchor: [0, -cy],
  });
}

export function ThreatPopupContent({ zone }: { zone: ThreatZone }) {
  const color = COLORS[zone.risk] ?? "#888";
  const pct = typeof zone.score === "number" ? Math.round(zone.score * 100) : null;
  const soilHot = zone.soilMoisture === "Saturated";
  return (
    <div style={{ fontFamily: "'IBM Plex Sans',sans-serif", background: "rgba(7,25,20,0.88)", color: "white", borderRadius: 10, minWidth: 220, overflow: "hidden", border: "1px solid rgba(255,255,255,0.08)" }}>
      <div style={{ padding: "12px 14px", borderBottom: "0.5px solid rgba(255,255,255,0.08)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
          <div style={{ fontSize: 13, fontWeight: 600 }}>{zone.name}</div>
          <span style={{ fontSize: 10, fontWeight: 600, padding: "2px 8px", borderRadius: 3, background: `${color}22`, color, textTransform: "uppercase" }}>{zone.risk}</span>
        </div>
        <div style={{ fontSize: 10, color: "rgba(255,255,255,0.4)" }}>{zone.district}</div>
      </div>
      <div style={{ padding: "10px 14px" }}>
        <div style={{ fontSize: 28, fontWeight: 700, color, fontFamily: "'IBM Plex Mono',monospace", lineHeight: 1, marginBottom: 8 }}>
          {pct === null ? "—" : `${pct}%`}<span style={{ fontSize: 12, color: "rgba(255,255,255,0.3)", fontWeight: 400, marginLeft: 6 }}>risk score</span>
        </div>
        <div style={{ height: 4, background: "rgba(255,255,255,0.08)", borderRadius: 2, marginBottom: 12, overflow: "hidden" }}>
          <div style={{ height: "100%", width: `${pct === null ? 0 : pct}%`, background: color, borderRadius: 2 }} />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 10 }}>
          <div>
            <div style={{ fontSize: 9, color: "rgba(255,255,255,0.3)", marginBottom: 2, letterSpacing: "0.06em" }}>RAINFALL</div>
            <div style={{ fontSize: 12, fontWeight: 500 }}>{zone.rainfall}</div>
          </div>
          <div>
            <div style={{ fontSize: 9, color: "rgba(255,255,255,0.3)", marginBottom: 2, letterSpacing: "0.06em" }}>SOIL</div>
            <div style={{ fontSize: 12, fontWeight: 500, color: soilHot ? "#D62828" : "#F2B705" }}>{zone.soilMoisture}</div>
          </div>
          <div>
            <div style={{ fontSize: 9, color: "rgba(255,255,255,0.3)", marginBottom: 2, letterSpacing: "0.06em" }}>SLOPE STRESS</div>
            <div style={{ fontSize: 12, fontWeight: 500 }}>{zone.slopeStress}</div>
          </div>
          <div>
            <div style={{ fontSize: 9, color: "rgba(255,255,255,0.3)", marginBottom: 2, letterSpacing: "0.06em" }}>TREND</div>
            <div style={{ fontSize: 12, fontWeight: 500, color }}>{zone.trend === "escalating" ? "↑ Escalating" : "→ Stable"}</div>
          </div>
        </div>
        <button
          type="button"
          className="dark-popup-view-btn"
          data-zone-id={zone.id}
          style={{ width: "100%", padding: 8, background: color, color: "white", border: "none", borderRadius: 6, fontSize: 12, fontWeight: 500, cursor: "pointer", fontFamily: "'IBM Plex Sans',sans-serif", textAlign: "center" }}
        >
          View full details →
        </button>
      </div>
    </div>
  );
}

interface ThreatMarkerProps {
  zone: ThreatZone;
  isSelected: boolean;
  onSelect: (zone: ThreatZone) => void;
}

export default function ThreatMarker({ zone, isSelected, onSelect }: ThreatMarkerProps) {
  const icon = makeThreatIcon(zone, isSelected);

  return (
    <Marker
      position={[zone.lat, zone.lng]}
      icon={icon}
      eventHandlers={{
        click: (e) => {
          L.DomEvent.stopPropagation(e.originalEvent);
          onSelect(zone);
        },
      }}
    >
      <Popup className="dark-popup" offset={[0, -SIZES[zone.risk].aura / 2 - 8]} closeButton maxWidth={260}>
        <ThreatPopupContent zone={zone} />
      </Popup>
    </Marker>
  );
}

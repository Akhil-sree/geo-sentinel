import { useEffect, useRef, useState } from "react";
import type { ZoneRisk } from "../../types/risk";

interface MapHoverCardProps {
  risk: ZoneRisk | null;
  position: { x: number; y: number } | null;
  visible: boolean;
  type: "hotspot" | "zone";
  hotspotCount?: number;
}

function getSeverityColor(severity: string): string {
  switch (severity) {
    case "VERY_HIGH": return "#B91C1C";
    case "HIGH": return "#E55A2B";
    case "MODERATE": return "#F2A623";
    default: return "#2563EB";
  }
}

function getSeverityLabel(severity: string): string {
  switch (severity) {
    case "VERY_HIGH": return "CRITICAL";
    case "HIGH": return "HIGH";
    case "MODERATE": return "MODERATE";
    default: return "LOW";
  }
}

function soilMoistureLabel(sm: number): string {
  if (sm > 0.45) return "Saturated";
  if (sm > 0.3) return "Moist";
  return "Normal";
}

function formatRiskScore(score: number | null | undefined): string {
  if (typeof score !== "number" || !Number.isFinite(score)) return "—";
  if (score > 1) return `${score.toFixed(0)}%`;
  return `${(score * 100).toFixed(0)}%`;
}

const cardStyle: React.CSSProperties = {
  background: "rgba(6, 21, 16, 0.82)",
  backdropFilter: "blur(7px)",
  WebkitBackdropFilter: "blur(7px)",
  border: "1px solid rgba(255,255,255,0.10)",
  borderRadius: 10,
  boxShadow: "0 12px 32px rgba(0,0,0,0.30)",
  color: "white",
};

const labelStyle: React.CSSProperties = {
  fontSize: 9,
  color: "rgba(255,255,255,0.35)",
  letterSpacing: "0.06em",
  marginBottom: 2,
};

const valueStyle: React.CSSProperties = {
  fontSize: 13,
  fontWeight: 500,
  color: "rgba(255,255,255,0.85)",
};

export default function MapHoverCard({ risk, position, visible, type, hotspotCount = 0 }: MapHoverCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [adjustedPos, setAdjustedPos] = useState<{ x: number; y: number } | null>(null);

  useEffect(() => {
    if (!position || !visible) {
      setAdjustedPos(null);
      return;
    }

    const card = cardRef.current;
    if (!card) {
      setAdjustedPos(position);
      return;
    }

    const rect = card.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    const cardW = rect.width || 280;
    const cardH = rect.height || 260;
    const rightPanelWidth = 424;
    const mapArea = vw - rightPanelWidth;
    const offset = 16;

    let x = position.x + offset;
    let y = position.y - cardH / 2;

    if (x + cardW > mapArea - 10) {
      x = position.x - cardW - offset;
    }
    if (x < 10) x = 10;
    if (y < 10) y = 10;
    if (y + cardH > vh - 10) y = vh - cardH - 10;

    setAdjustedPos({ x, y });
  }, [position, visible]);

  if (!visible || !risk || !adjustedPos) return null;

  const severityColor = getSeverityColor(risk.severity);
  const severityLabel = getSeverityLabel(risk.severity);

  if (type === "zone") {
    return (
      <div
        ref={cardRef}
        className="fixed z-[1000] pointer-events-none"
        style={{ left: adjustedPos.x, top: adjustedPos.y, width: 280 }}
      >
        <div style={cardStyle}>
          {/* Header */}
          <div style={{ padding: "10px 14px", borderBottom: "0.5px solid rgba(255,255,255,0.08)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: severityColor, letterSpacing: "0.04em" }}>
              {severityLabel} RISK ZONE
            </span>
            <div style={{ width: 7, height: 7, borderRadius: "50%", background: severityColor, animation: "hud-pulse 1.5s ease infinite" }} />
          </div>

          {/* Content */}
          <div style={{ padding: "10px 14px" }}>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 2 }}>{risk.name}</div>
            <div style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", marginBottom: 10 }}>{risk.district} · Meghalaya</div>

            {hotspotCount > 0 && (
              <div style={{ fontSize: 11, color: "rgba(255,255,255,0.5)", marginBottom: 8 }}>
                {hotspotCount} landslide {hotspotCount === 1 ? "hotspot" : "hotspots"} detected
              </div>
            )}

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              <div>
                <div style={labelStyle}>RISK LEVEL</div>
                <div style={{ ...valueStyle, color: severityColor, fontWeight: 600 }}>{severityLabel}</div>
              </div>
              <div>
                <div style={labelStyle}>72H RAINFALL</div>
                <div style={valueStyle}>{risk.rainfall_72h?.toFixed(0) ?? "—"} mm</div>
              </div>
              <div>
                <div style={labelStyle}>SOIL MOISTURE</div>
                <div style={{ ...valueStyle, color: risk.soil_moisture > 0.45 ? "#B91C1C" : "#F2A623" }}>{soilMoistureLabel(risk.soil_moisture)}</div>
              </div>
              <div>
                <div style={labelStyle}>RISK SCORE</div>
                <div style={{ ...valueStyle, color: severityColor, fontFamily: "IBM Plex Mono" }}>{formatRiskScore(risk.risk_score)}</div>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div style={{ padding: "8px 14px", borderTop: "0.5px solid rgba(255,255,255,0.06)", textAlign: "center" }}>
            <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)" }}>Click for full details →</span>
          </div>
        </div>
      </div>
    );
  }

  // Hotspot card
  return (
    <div
      ref={cardRef}
      className="fixed z-[1000] pointer-events-none"
      style={{ left: adjustedPos.x, top: adjustedPos.y, width: 280 }}
    >
      <div style={cardStyle}>
        {/* Header */}
        <div style={{ padding: "10px 14px", borderBottom: "0.5px solid rgba(255,255,255,0.08)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 11, fontWeight: 600, color: severityColor, letterSpacing: "0.04em" }}>
            {severityLabel} RISK
          </span>
          {risk.escalated && (
            <span style={{ fontSize: 9, fontWeight: 600, padding: "2px 6px", borderRadius: 3, background: "#B91C1C33", color: "#B91C1C" }}>
              ESCALATED
            </span>
          )}
        </div>

        {/* Content */}
        <div style={{ padding: "10px 14px" }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 2 }}>{risk.name}</div>
          <div style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", marginBottom: 10 }}>{risk.district} · Meghalaya</div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <div>
              <div style={labelStyle}>RISK SCORE</div>
              <div style={{ ...valueStyle, color: severityColor, fontFamily: "IBM Plex Mono", fontWeight: 600 }}>{formatRiskScore(risk.risk_score)}</div>
            </div>
            <div>
              <div style={labelStyle}>72H RAINFALL</div>
              <div style={valueStyle}>{risk.rainfall_72h?.toFixed(0) ?? "—"} mm</div>
            </div>
            <div>
              <div style={labelStyle}>SOIL MOISTURE</div>
              <div style={{ ...valueStyle, color: risk.soil_moisture > 0.45 ? "#B91C1C" : "#F2A623" }}>{soilMoistureLabel(risk.soil_moisture)}</div>
            </div>
            {risk.slope_stress_score != null && (
              <div>
                <div style={labelStyle}>SLOPE STRESS</div>
                <div style={valueStyle}>{risk.slope_stress_score > 1 ? `${risk.slope_stress_score.toFixed(0)}%` : `${(risk.slope_stress_score * 100).toFixed(0)}%`}</div>
              </div>
            )}
          </div>

          <div style={{ marginTop: 10, paddingTop: 8, borderTop: "0.5px solid rgba(255,255,255,0.06)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: 11, color: "rgba(255,255,255,0.4)" }}>Trend</span>
              <span style={{ fontSize: 11, fontWeight: 500, color: risk.escalated ? "#E55A2B" : "#2563EB" }}>
              {risk.escalated ? "↑ Escalated" : "→ Stable"}
            </span>
          </div>
        </div>

        {/* Footer */}
        <div style={{ padding: "8px 14px", borderTop: "0.5px solid rgba(255,255,255,0.06)", textAlign: "center" }}>
          <span style={{ fontSize: 10, color: "rgba(255,255,255,0.3)" }}>Click for full details →</span>
        </div>
      </div>
    </div>
  );
}

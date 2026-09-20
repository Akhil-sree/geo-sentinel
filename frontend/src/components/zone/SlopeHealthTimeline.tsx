import { useEffect, useState } from "react";
import { getRiskTrajectory } from "../../api/risk";
import type { TrajectoryPoint } from "../../types/risk";

const FILL_PERCENT: Record<string, string> = {
  STABLE: "30%",
  STRESSED: "60%",
  DEGRADING: "85%",
  CRITICAL: "100%",
};

const GRADIENT: Record<string, string> = {
  STABLE: "linear-gradient(to right, #2563EB, #93B4F5)",
  STRESSED: "linear-gradient(to right, #F2A623, #FDE68A)",
  DEGRADING: "linear-gradient(to right, #E55A2B, #FCA97A)",
  CRITICAL: "linear-gradient(to right, #B91C1C, #E55A2B)",
};

function fmtTime(iso: string): string {
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, "0")}h`;
}

export default function SlopeHealthTimeline({ zoneId }: { zoneId: string }) {
  const [data, setData] = useState<TrajectoryPoint[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    getRiskTrajectory(zoneId)
      .then((r) => { if (!cancelled) setData(r.trajectory || []); })
      .catch(() => { if (!cancelled) setData([]); });
    return () => { cancelled = true; };
  }, [zoneId]);

  if (data === null) {
    return (
      <div className="rounded-card p-4" style={{
        background: 'rgba(255, 255, 255, 0.55)',
        border: '1px solid rgba(255, 255, 255, 0.30)',
      }}>
        <p className="text-[13px] text-gs-text-secondary">Loading slope health…</p>
      </div>
    );
  }

  const segs = data.slice(-6);
  if (segs.length === 0) {
    return (
      <div className="rounded-card p-4" style={{
        background: 'rgba(255, 255, 255, 0.55)',
        border: '1px solid rgba(255, 255, 255, 0.30)',
      }}>
        <div style={{ fontSize: 15, fontWeight: 500, color: "#1A3C2E" }}>
          Slope Health Timeline
        </div>
        <p className="mt-1 text-[13px] text-gs-text-secondary">
          No slope-state history yet — move the event scrubber to generate it.
        </p>
      </div>
    );
  }

  const last = segs[segs.length - 1];
  const worsening = segs.length > 1
    && segs[segs.length - 1].risk_score >= segs[0].risk_score;

  return (
    <div className="rounded-card p-4" style={{
      background: 'rgba(255, 255, 255, 0.55)',
      backdropFilter: 'blur(4px)',
      WebkitBackdropFilter: 'blur(4px)',
      border: '1px solid rgba(255, 255, 255, 0.30)',
      boxShadow: '0 2px 10px rgba(15, 35, 27, 0.04)',
    }}>
      {/* Header with live indicator */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
        <div>
          <div style={{
            fontSize: 15, fontWeight: 500, color: "#1A3C2E",
            display: "flex", alignItems: "center", gap: 6,
          }}>
            Slope Health Timeline
            <span style={{
              width: 7, height: 7, borderRadius: "50%",
              background: last.slope_state_color, display: "inline-block",
              animation: "pulse-dot 1.5s ease infinite",
            }} />
          </div>
          <div style={{ fontSize: 12, color: "#9CA3AF", marginTop: 2 }}>
            State progression · {segs.length} recorded steps
          </div>
        </div>
        <span style={{
          fontSize: 12, padding: "3px 8px", borderRadius: 3,
          background: `${last.slope_state_color}18`, color: last.slope_state_color, fontWeight: 600,
        }}>
          {worsening ? "↑ Worsening" : "↓ Improving"}
        </span>
      </div>

      {/* Timeline rows with gradient fill bars */}
      <div style={{ padding: "0 4px" }}>
        {segs.map((seg, i) => {
          const isNow = i === segs.length - 1;
          return (
            <div
              key={seg.timestamp + i}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginBottom: 7,
              }}
            >
              {/* Time */}
              <div style={{
                fontSize: 12,
                fontFamily: "IBM Plex Mono",
                color: "#9CA3AF",
                minWidth: 36,
                textAlign: "right",
              }}>
                {isNow ? "Now" : fmtTime(seg.timestamp)}
              </div>

              {/* Dot */}
              <div style={{
                width: isNow ? 12 : 9,
                height: isNow ? 12 : 9,
                borderRadius: "50%",
                background: seg.slope_state_color,
                flexShrink: 0,
                boxShadow: isNow ? `0 0 0 3px ${seg.slope_state_color}40` : "none",
                animation: isNow ? "pulse-dot 1.5s ease-in-out infinite" : "none",
              }} />

              {/* Gradient bar track */}
              <div style={{
                flex: 1,
                height: 10,
                background: "#F3F4F6",
                borderRadius: 5,
                overflow: "hidden",
                position: "relative",
              }}>
                <div style={{
                  height: "100%",
                  width: FILL_PERCENT[seg.slope_state] ?? "30%",
                  background: GRADIENT[seg.slope_state] ?? GRADIENT.STABLE,
                  borderRadius: 5,
                  transition: "width 0.8s ease",
                  position: "relative",
                }}>
                  {/* Shimmer effect */}
                  <div style={{
                    position: "absolute",
                    top: 0, bottom: 0, right: 0,
                    width: 20,
                    background: "rgba(255,255,255,0.4)",
                    filter: "blur(3px)",
                  }} />
                </div>
              </div>

              {/* State label */}
              <div style={{
                fontSize: 12,
                fontWeight: isNow ? 600 : 400,
                color: isNow ? seg.slope_state_color : "#6B7280",
                minWidth: 60,
                textAlign: "right",
              }}>
                {seg.slope_state_label}
              </div>

              {/* Risk score */}
              <span style={{
                fontSize: 12,
                fontFamily: "IBM Plex Mono",
                color: "#9CA3AF",
                marginLeft: 6,
              }}>
                {seg.risk_score.toFixed(2)}
              </span>
            </div>
          );
        })}
      </div>

      {/* Bottom status bar — 3-column strip */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr 1fr",
        gap: 0,
        marginTop: 14,
        background: `${last.slope_state_color}10`,
        borderRadius: 8,
        border: `0.5px solid ${last.slope_state_color}30`,
        overflow: "hidden",
      }}>
        <div style={{ padding: "10px 12px", borderRight: `0.5px solid ${last.slope_state_color}30` }}>
          <div style={{ fontSize: 11, color: "#9CA3AF", letterSpacing: "0.06em", marginBottom: 3 }}>STATE</div>
          <div style={{
            fontSize: 13, fontWeight: 600, color: last.slope_state_color,
            display: "flex", alignItems: "center", gap: 5,
          }}>
            <div style={{
              width: 7, height: 7, borderRadius: "50%",
              background: last.slope_state_color,
              animation: "pulse-dot 1.5s ease infinite",
            }} />
            {last.slope_state_label}
          </div>
        </div>
        <div style={{ padding: "10px 12px", borderRight: `0.5px solid ${last.slope_state_color}30` }}>
          <div style={{ fontSize: 11, color: "#9CA3AF", letterSpacing: "0.06em", marginBottom: 3 }}>RISK NOW</div>
          <div style={{
            fontSize: 13, fontWeight: 600, color: last.slope_state_color,
            fontFamily: "IBM Plex Mono",
          }}>
            {(last.risk_score * 100).toFixed(0)}%
          </div>
        </div>
        <div style={{ padding: "10px 12px" }}>
          <div style={{ fontSize: 11, color: "#9CA3AF", letterSpacing: "0.06em", marginBottom: 3 }}>TREND</div>
          <div style={{ fontSize: 13, fontWeight: 600, color: last.slope_state_color }}>
            {worsening ? "↑ Worsening" : "↓ Improving"}
          </div>
        </div>
      </div>
    </div>
  );
}

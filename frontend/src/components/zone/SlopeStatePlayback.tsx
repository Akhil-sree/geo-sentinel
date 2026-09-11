import { useEffect, useState, useRef, useCallback } from "react";
import { getRiskTrajectory } from "../../api/risk";
import type { TrajectoryPoint } from "../../types/risk";

const STATE_COLORS: Record<string, string> = {
  STABLE: "#245c45",
  STRESSED: "#d97706",
  DEGRADING: "#ea580c",
  CRITICAL: "#ba1a1a",
};

const STATE_ICONS: Record<string, string> = {
  STABLE: "\u2713",
  STRESSED: "\u26A0",
  DEGRADING: "\u25B2",
  CRITICAL: "\u26D4",
};

const STATE_DESCRIPTIONS: Record<string, string> = {
  STABLE: "Slope conditions within normal range",
  STRESSED: "Early warning — environmental stress detected",
  DEGRADING: "Active deterioration — monitor closely",
  CRITICAL: "Critical instability — immediate attention",
};

interface SlopeStatePlaybackProps {
  zoneId: string;
  onStateChange?: (state: string, color: string, risk: number) => void;
}

export default function SlopeStatePlayback({ zoneId, onStateChange }: SlopeStatePlaybackProps) {
  const [points, setPoints] = useState<TrajectoryPoint[]>([]);
  const [playing, setPlaying] = useState(false);
  const [currentIdx, setCurrentIdx] = useState(-1);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    setLoading(true);
    getRiskTrajectory(zoneId)
      .then((r) => {
        setPoints(r.trajectory);
        setCurrentIdx(r.trajectory.length - 1);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [zoneId]);

  const stop = useCallback(() => {
    setPlaying(false);
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
  }, []);

  const play = useCallback(() => {
    if (points.length === 0) return;
    setPlaying(true);
    setCurrentIdx(0);
    let idx = 0;
    timerRef.current = window.setInterval(() => {
      idx++;
      if (idx >= points.length) { stop(); return; }
      setCurrentIdx(idx);
    }, 700);
  }, [points, stop]);

  const restart = useCallback(() => {
    stop();
    setCurrentIdx(0);
  }, [stop]);

  useEffect(() => () => { if (timerRef.current) clearInterval(timerRef.current); }, []);

  useEffect(() => {
    if (currentIdx >= 0 && currentIdx < points.length) {
      const p = points[currentIdx];
      onStateChange?.(p.slope_state, p.slope_state_color, p.risk_score);
    }
  }, [currentIdx, points, onStateChange]);

  if (loading) {
    return (
      <div className="rounded-lg border border-[#d9e2d9] bg-white p-3 shadow-sm">
        <div className="flex items-center gap-2">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-[#04442f] border-t-transparent" />
          <span className="text-[10px] text-[#707973]">Loading slope trajectory...</span>
        </div>
      </div>
    );
  }
  if (points.length === 0) return null;

  const current = currentIdx >= 0 ? points[currentIdx] : points[points.length - 1];
  const progress = points.length > 1 ? (currentIdx / (points.length - 1)) * 100 : 100;

  const stateCounts = points.reduce((acc, p) => {
    acc[p.slope_state] = (acc[p.slope_state] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  // Find state transitions
  const transitions: { from: string; to: string; at: number }[] = [];
  for (let i = 1; i < points.length; i++) {
    if (points[i].slope_state !== points[i - 1].slope_state) {
      transitions.push({ from: points[i - 1].slope_state, to: points[i].slope_state, at: i });
    }
  }

  return (
    <div className="overflow-hidden rounded-lg border border-[#d9e2d9] bg-white shadow-sm">
      {/* Header */}
      <div className="border-b border-[#e4e3db] bg-[#f8f7f3] px-3 py-2">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wide text-[#1b1c17]">
              Slope State Evolution
            </p>
            <p className="text-[8px] text-[#707973]">
              Animated playback of slope health over the observation window
            </p>
          </div>
          <div className="flex items-center gap-1.5">
            <button
              onClick={restart}
              className="flex h-7 w-7 items-center justify-center rounded-full border border-[#d9e2d9] bg-white text-[#404943] hover:bg-[#f0eee6] transition-colors"
              title="Restart"
            >
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M2 6a4 4 0 1 1 1 2.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                <path d="M2 3v3h3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
            <button
              onClick={playing ? stop : play}
              className="flex h-8 w-8 items-center justify-center rounded-full bg-[#04442f] text-white hover:bg-[#0a5c40] transition-colors shadow-sm"
            >
              {playing ? (
                <svg width="12" height="12" viewBox="0 0 12 12"><rect x="2" y="1" width="3" height="10" rx="0.5" fill="white"/><rect x="7" y="1" width="3" height="10" rx="0.5" fill="white"/></svg>
              ) : (
                <svg width="12" height="12" viewBox="0 0 12 12"><polygon points="3,1 11,6 3,11" fill="white"/></svg>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Current State Hero */}
      <div className="px-3 pt-3 pb-2">
        <div
          className="rounded-lg border-2 p-3 transition-all duration-500"
          style={{
            borderColor: (current?.slope_state_color || "#707973"),
            backgroundColor: (current?.slope_state_color || "#707973") + "08",
          }}
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span
                  className="flex h-7 w-7 items-center justify-center rounded-full text-sm font-bold text-white"
                  style={{ backgroundColor: current?.slope_state_color || "#707973" }}
                >
                  {STATE_ICONS[current?.slope_state || "STABLE"]}
                </span>
                <div>
                  <span className="text-base font-bold" style={{ color: current?.slope_state_color || "#707973" }}>
                    {current?.slope_state_label || current?.slope_state || "—"}
                  </span>
                  <p className="text-[8px] text-[#707973]">
                    {STATE_DESCRIPTIONS[current?.slope_state || "STABLE"]}
                  </p>
                </div>
              </div>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold" style={{ color: current?.slope_state_color || "#707973" }}>
                {current ? (current.risk_score * 100).toFixed(1) : "—"}%
              </p>
              <p className="text-[8px] text-[#707973]">Risk Score</p>
            </div>
          </div>

          {/* Stress gauge */}
          <div className="mt-2">
            <div className="flex justify-between text-[7px] text-[#707973] mb-0.5">
              <span>Stress Level</span>
              <span className="font-bold" style={{ color: current?.slope_state_color }}>
                {current ? (current.risk_score * 100).toFixed(0) : 0}%
              </span>
            </div>
            <div className="h-2.5 w-full rounded-full bg-[#e4e3db] overflow-hidden">
              <div
                className="h-2.5 rounded-full transition-all duration-500"
                style={{
                  width: `${Math.min(100, (current?.risk_score || 0) * 100)}%`,
                  backgroundColor: current?.slope_state_color || "#707973",
                }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Playback Progress */}
      <div className="px-3 pb-2">
        <div className="flex items-center justify-between text-[8px] text-[#707973] mb-1">
          <span>Step {currentIdx + 1} of {points.length}</span>
          <span>{playing ? "Playing..." : "Paused"}</span>
        </div>
        <div className="h-1.5 w-full rounded-full bg-[#e4e3db]">
          <div
            className="h-1.5 rounded-full bg-[#04442f] transition-all duration-200"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* State Timeline */}
      <div className="border-t border-[#e4e3db] px-3 py-2">
        <p className="mb-1.5 text-[8px] font-bold uppercase tracking-wider text-[#707973]">
          State Timeline
        </p>
        <div className="flex items-center gap-0.5 overflow-x-auto pb-1">
          {points.filter((_, i) => i === 0 || i === points.length - 1 || i % Math.max(1, Math.floor(points.length / 8)) === 0).map((p, i) => {
            const isActive = currentIdx >= 0 && points.indexOf(p) <= currentIdx;
            const color = STATE_COLORS[p.slope_state] || "#707973";
            const isTransition = transitions.some((t) => t.at === points.indexOf(p));

            return (
              <div key={i} className="flex flex-col items-center min-w-[36px]">
                <span
                  className={`text-[7px] font-bold mb-0.5 ${isActive ? "" : "opacity-30"}`}
                  style={{ color: isActive ? color : "#ccc" }}
                >
                  {p.slope_state_label?.slice(0, 3) || p.slope_state?.slice(0, 3)}
                </span>
                <div
                  className={`h-3 w-7 rounded-sm transition-all duration-300 ${isActive ? "" : "opacity-25"} ${isTransition ? "ring-1 ring-offset-1" : ""}`}
                  style={{
                    backgroundColor: isActive ? color : "#e4e3db",
                  }}
                />
                <span className="text-[6px] text-[#707973] mt-0.5">
                  {new Date(p.timestamp).getHours()}h
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* State Distribution */}
      <div className="border-t border-[#e4e3db] px-3 py-2">
        <p className="mb-1.5 text-[8px] font-bold uppercase tracking-wider text-[#707973]">
          State Distribution
        </p>
        <div className="flex gap-1">
          {["STABLE", "STRESSED", "DEGRADING", "CRITICAL"].map((state) => {
            const count = stateCounts[state] || 0;
            const pct = points.length > 0 ? (count / points.length * 100) : 0;
            if (count === 0) return null;
            return (
              <div key={state} className="flex-1 rounded border p-1 text-center" style={{ borderColor: STATE_COLORS[state] + "30", backgroundColor: STATE_COLORS[state] + "08" }}>
                <span className="block text-[7px] font-bold" style={{ color: STATE_COLORS[state] }}>
                  {STATE_ICONS[state]} {state.slice(0, 4)}
                </span>
                <span className="block text-[10px] font-bold text-[#1b1c17]">{count}</span>
                <span className="block text-[6px] text-[#707973]">{pct.toFixed(0)}%</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Transitions Log */}
      {transitions.length > 0 && (
        <div className="border-t border-[#e4e3db] px-3 py-2">
          <p className="mb-1 text-[8px] font-bold uppercase tracking-wider text-[#707973]">
            State Changes Detected
          </p>
          <div className="space-y-0.5">
            {transitions.slice(-3).map((t, i) => (
              <div key={i} className="flex items-center gap-1 text-[8px]">
                <span className="rounded px-1 py-0.5 text-[7px] font-bold text-white" style={{ backgroundColor: STATE_COLORS[t.from] }}>
                  {t.from.slice(0, 3)}
                </span>
                <svg width="10" height="8" viewBox="0 0 10 8" className="text-[#707973]">
                  <path d="M0 4h8M6 1l3 3-3 3" stroke="currentColor" strokeWidth="1" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                <span className="rounded px-1 py-0.5 text-[7px] font-bold text-white" style={{ backgroundColor: STATE_COLORS[t.to] }}>
                  {t.to.slice(0, 3)}
                </span>
                <span className="text-[7px] text-[#707973]">at step {t.at + 1}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

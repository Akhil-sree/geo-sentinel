import { useEffect, useState, useRef } from "react";
import { getCellGrid, getTemporalCellGrid } from "../../api/risk";
import { useUIStore } from "../../store/uiStore";
import { fmtPctOpt } from "../../lib/format";
import Spinner from "../common/Spinner";
import type { CellGridCell, TemporalCellGridTimestep } from "../../types/risk";

const SEVERITY_COLORS: Record<string, string> = {
  LOW: "#2563EB",
  MODERATE: "#d97706",
  HIGH: "#ea580c",
  VERY_HIGH: "#ba1a1a",
};

const STATE_COLORS: Record<string, string> = {
  CRITICAL: "#ba1a1a",
  DEGRADING: "#ea580c",
  STRESSED: "#d97706",
  STABLE: "#2563EB",
};

export default function CellRiskGrid() {
  const simTime = useUIStore((s) => s.simTime);
  const selectedZoneId = useUIStore((s) => s.selectedZoneId);
  const [cells, setCells] = useState<CellGridCell[]>([]);
  const [loading, setLoading] = useState(false);
  const [zoneName, setZoneName] = useState("");
  const [cellMethod, setCellMethod] = useState("");
  const [resolution, setResolution] = useState(20);
  const [frames, setFrames] = useState<TemporalCellGridTimestep[]>([]);
  const [frameMethod, setFrameMethod] = useState("");
  const [frameIdx, setFrameIdx] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [framesLoading, setFramesLoading] = useState(false);
  const [framesError, setFramesError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!selectedZoneId) return;
    setLoading(true);
    getCellGrid(selectedZoneId, simTime, resolution)
      .then((data) => {
        setCells(data.cells || []);
        setZoneName(data.name || "");
        setCellMethod(data.cell_method || "");
      })
      .catch(() => { setCells([]); })
      .finally(() => setLoading(false));
  }, [selectedZoneId, simTime, resolution]);

  useEffect(() => {
    setFrames([]);
    setFrameMethod("");
    setFrameIdx(0);
    setPlaying(false);
    setFramesError(null);
    if (timerRef.current) clearInterval(timerRef.current);
  }, [selectedZoneId]);

  useEffect(() => {
    if (playing && frames.length > 0) {
      timerRef.current = setInterval(() => {
        setFrameIdx((i) => (i + 1) % frames.length);
      }, 1200);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [playing, frames.length]);

  const loadTemporal = () => {
    if (!selectedZoneId) return;
    setFramesLoading(true);
    setFramesError(null);
    getTemporalCellGrid(selectedZoneId, 12)
      .then((data) => {
        setFrames(data.timesteps || []);
        setFrameMethod(data.cell_method || "");
        setFrameIdx(0);
        setPlaying((data.timesteps || []).length > 0);
      })
      .catch(() => setFramesError("Temporal grid unavailable — is the backend running?"))
      .finally(() => setFramesLoading(false));
  };

  if (!selectedZoneId) return null;

  if (loading) {
    return (
      <div className="p-3">
        <div className="flex items-center gap-2 text-[13px] text-gs-text-secondary">
          <Spinner /> Loading cell risk grid…
        </div>
      </div>
    );
  }

  if (!cells.length) return null;

  const criticalCount = cells.filter((c) => c.slope_state === "CRITICAL").length;
  const degradingCount = cells.filter((c) => c.slope_state === "DEGRADING").length;
  const stressedCount = cells.filter((c) => c.slope_state === "STRESSED").length;
  const stableCount = cells.filter((c) => c.slope_state === "STABLE").length;
  const numScores = cells.map((c) => c.risk_score).filter((v): v is number => typeof v === "number");
  const avgRisk = numScores.length ? numScores.reduce((s, v) => s + v, 0) / numScores.length : null;
  const maxRisk = numScores.length ? Math.max(...numScores) : null;

  // Build a grid layout for spatial visualization
  const gridSize = Math.ceil(Math.sqrt(cells.length));

  return (
    <div>
      {/* Section header — institutional style */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="gs-label">Per-Cell Risk Grid</div>
          <p className="text-[11px] text-gs-text-secondary mt-0.5">
            {zoneName} · {cells.length} terrain cells
          </p>
        </div>
        <select
          value={resolution}
          onChange={(e) => setResolution(Number(e.target.value))}
          className="rounded-md border border-gs-border bg-white px-2 py-1 text-[11px] text-gs-text"
        >
          <option value={12}>Low</option>
          <option value={20}>Medium</option>
          <option value={28}>High</option>
        </select>
      </div>

      {/* Summary stats — compact */}
      <div className="grid grid-cols-4 gap-1.5 mb-3">
        {[
          { label: "Avg", value: fmtPctOpt(avgRisk), color: "#d97706" },
          { label: "Max", value: fmtPctOpt(maxRisk), color: "#ba1a1a" },
          { label: "Critical", value: String(criticalCount), color: "#ba1a1a" },
          { label: "Stable", value: String(stableCount), color: "#2563EB" },
        ].map((s) => (
          <div key={s.label} className="text-center rounded-md px-1 py-1.5" style={{ background: '#F4F1EB' }}>
            <div className="text-[14px] font-bold" style={{ color: s.color }}>{s.value}</div>
            <div className="text-[9px] font-bold uppercase tracking-wide text-gs-text-secondary">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Spatial Risk Distribution — grid heatmap */}
      <div className="rounded-lg p-3 mb-3" style={{ background: '#F4F1EB' }}>
        <div className="flex items-center justify-between mb-2">
          <div className="gs-label">Spatial Risk Distribution</div>
        </div>
        {cellMethod && (
          <p className="text-[9px] italic text-gs-text-secondary mb-2">{cellMethod}</p>
        )}

        {/* Grid visualization */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${gridSize}, 1fr)`,
          gap: 2,
        }}>
          {cells.map((cell, i) => (
            <div
              key={i}
              className="rounded-sm cursor-crosshair"
              style={{
                background: SEVERITY_COLORS[cell.severity] || "#999",
                opacity: typeof cell.risk_score === "number" ? 0.35 + cell.risk_score * 0.65 : 0.35,
                aspectRatio: '1',
                minWidth: 6,
                minHeight: 6,
              }}
              title={`Cell ${i + 1} · Risk: ${fmtPctOpt(cell.risk_score)} · State: ${cell.slope_state}`}
            />
          ))}
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3 mt-2 text-[9px] text-gs-text-secondary">
          {Object.entries(SEVERITY_COLORS).map(([key, color]) => (
            <span key={key} className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-sm inline-block" style={{ background: color }} />
              {key.replace("_", " ")}
            </span>
          ))}
        </div>
      </div>

      {/* Slope State Breakdown — compact with distribution bar */}
      <div className="mb-3">
        <div className="gs-label mb-2">Slope State Breakdown</div>

        {/* Distribution bar */}
        <div className="flex h-2 rounded-full overflow-hidden mb-2" style={{ background: '#E5E7EB' }}>
          {[
            { count: criticalCount, color: STATE_COLORS.CRITICAL },
            { count: degradingCount, color: STATE_COLORS.DEGRADING },
            { count: stressedCount, color: STATE_COLORS.STRESSED },
            { count: stableCount, color: STATE_COLORS.STABLE },
          ].map((seg, i) => (
            <div
              key={i}
              style={{
                width: `${(seg.count / cells.length) * 100}%`,
                background: seg.color,
                transition: 'width 0.5s ease',
              }}
            />
          ))}
        </div>

        {/* State labels */}
        <div className="space-y-1">
          {([
            { state: "CRITICAL", count: criticalCount, color: STATE_COLORS.CRITICAL },
            { state: "DEGRADING", count: degradingCount, color: STATE_COLORS.DEGRADING },
            { state: "STRESSED", count: stressedCount, color: STATE_COLORS.STRESSED },
            { state: "STABLE", count: stableCount, color: STATE_COLORS.STABLE },
          ] as const).map((item) => (
            <div key={item.state} className="flex items-center gap-2">
              <span className="w-16 text-[10px] text-gs-text-secondary uppercase tracking-wide">{item.state.toLowerCase()}</span>
              <div className="flex-1">
                <div className="h-1.5 rounded-full bg-gs-border overflow-hidden">
                  <div className="h-full rounded-full transition-all" style={{
                    width: `${(item.count / cells.length) * 100}%`,
                    background: item.color,
                  }} />
                </div>
              </div>
              <span className="w-8 text-right text-[11px] font-bold tabular-nums" style={{ color: item.color }}>
                {item.count}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Temporal Animation — honestly labeled */}
      <div className="rounded-lg p-3" style={{ background: '#F4F1EB' }}>
        <div className="flex items-center justify-between mb-2">
          <div>
            <div className="gs-label">Cell Risk Timeline</div>
            <p className="text-[9px] text-gs-text-secondary mt-0.5">
              {frames.length > 0
                ? `${frames.length} timesteps · ${frames[0]?.label} → ${frames[frames.length - 1]?.label}`
                : "Per-cell risk evolution over simulation time"}
            </p>
            {frameMethod && (
              <p className="text-[9px] italic text-gs-text-secondary mt-0.5">{frameMethod}</p>
            )}
          </div>
          {frames.length === 0 ? (
            <button
              onClick={loadTemporal}
              disabled={framesLoading}
              className="rounded-md bg-forest px-2.5 py-1 text-[11px] font-semibold text-white transition hover:bg-forest-800 disabled:opacity-50"
            >
              {framesLoading ? "Loading…" : "▶ Load Timeline"}
            </button>
          ) : (
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPlaying((p) => !p)}
                className="rounded-md bg-forest px-2 py-1 text-[11px] font-semibold text-white transition hover:bg-forest-800"
              >
                {playing ? "⏸" : "▶"}
              </button>
              <button
                onClick={() => setFrameIdx((i) => (i + 1) % frames.length)}
                className="rounded-md px-2 py-1 text-[11px] font-semibold text-gs-text-secondary transition hover:bg-gs-surface"
              >
                →
              </button>
            </div>
          )}
        </div>

        {framesError && <p className="text-[11px] text-risk-critical">{framesError}</p>}

        {frames.length > 0 && (
          <>
            {/* Timeline selector */}
            <div className="mb-2 flex items-center gap-0.5">
              {frames.map((f, i) => (
                <button
                  key={f.t}
                  onClick={() => { setFrameIdx(i); setPlaying(false); }}
                  className="flex-1 rounded px-0.5 py-1 text-[10px] font-semibold transition"
                  style={{
                    background: i === frameIdx ? '#075240' : '#FFFFFF',
                    color: i === frameIdx ? '#FFFFFF' : '#5F6B62',
                  }}
                >
                  {f.label}
                </button>
              ))}
            </div>

            {/* Current frame grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: `repeat(${gridSize}, 1fr)`,
              gap: 2,
            }}>
              {frames[frameIdx].cells.map((cell, i) => (
                <div
                  key={i}
                  className="rounded-sm"
                  style={{
                    background: cell.slope_state_color,
                    opacity: typeof cell.risk_score === "number" ? 0.35 + cell.risk_score * 0.65 : 0.35,
                    aspectRatio: '1',
                    minWidth: 6,
                    minHeight: 6,
                  }}
                  title={`${frames[frameIdx].label} · Risk: ${fmtPctOpt(cell.risk_score)} · State: ${cell.slope_state}`}
                />
              ))}
            </div>

            <p className="mt-2 text-[10px] text-gs-text-secondary">
              {frames[frameIdx].label}: avg risk {fmtPctOpt(
                frames[frameIdx].cells.reduce((s, c) => s + (typeof c.risk_score === "number" ? c.risk_score : 0), 0) / Math.max(1, frames[frameIdx].cells.length)
              )} ·{" "}
              {frames[frameIdx].cells.filter((c) => c.slope_state === "CRITICAL").length} critical cells
            </p>
          </>
        )}
      </div>
    </div>
  );
}

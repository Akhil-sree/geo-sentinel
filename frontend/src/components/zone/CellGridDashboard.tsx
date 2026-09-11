import { useEffect, useState } from "react";
import { getCellGrid } from "../../api/risk";
import { useUIStore } from "../../store/uiStore";
import type { CellData } from "../../api/risk";

const FLAGSHIP_ZONE = "Z1";

const STATE_COLORS: Record<string, string> = {
  STABLE: "#245c45",
  STRESSED: "#d97706",
  DEGRADING: "#ea580c",
  CRITICAL: "#ba1a1a",
};

export default function CellGridDashboard({ zoneId }: { zoneId: string }) {
  const [cells, setCells] = useState<CellData[]>([]);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const simTime = useUIStore((s) => s.simTime);

  useEffect(() => {
    if (zoneId !== FLAGSHIP_ZONE) return;
    setLoading(true);
    getCellGrid(zoneId, simTime, 18)
      .then((r) => setCells(r.cells))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [zoneId, simTime]);

  if (zoneId !== FLAGSHIP_ZONE) return null;

  return (
    <div className="overflow-hidden rounded-lg border border-[#04442f]/20 bg-white shadow-sm">
      {/* Header with badge */}
      <div className="border-b border-[#e4e3db] bg-gradient-to-r from-[#04442f] to-[#0a5c40] px-3 py-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded bg-white/20 text-[10px] font-bold text-white">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <rect x="1" y="1" width="4" height="4" rx="0.5" fill="white" opacity="0.8"/>
                <rect x="5" y="1" width="4" height="4" rx="0.5" fill="white"/>
                <rect x="9" y="1" width="4" height="4" rx="0.5" fill="white" opacity="0.6"/>
                <rect x="1" y="5" width="4" height="4" rx="0.5" fill="white" opacity="0.6"/>
                <rect x="5" y="5" width="4" height="4" rx="0.5" fill="white" opacity="0.9"/>
                <rect x="9" y="5" width="4" height="4" rx="0.5" fill="white" opacity="0.4"/>
                <rect x="1" y="9" width="4" height="4" rx="0.5" fill="white" opacity="0.4"/>
                <rect x="5" y="9" width="4" height="4" rx="0.5" fill="white" opacity="0.7"/>
                <rect x="9" y="9" width="4" height="4" rx="0.5" fill="white" opacity="0.3"/>
              </svg>
            </span>
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wide text-white">
                Per-Cell Terrain Intelligence
              </p>
              <p className="text-[8px] text-white/70">
                RF model runs on each 400m terrain cell independently
              </p>
            </div>
          </div>
          <span className="rounded bg-white/20 px-1.5 py-0.5 text-[8px] font-bold text-white">
            {cells.length} CELLS
          </span>
        </div>
      </div>

      {loading ? (
        <div className="p-4">
          <div className="flex items-center gap-3">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-[#04442f] border-t-transparent" />
            <div>
              <p className="text-[10px] font-bold text-[#1b1c17]">Computing per-cell risk...</p>
              <p className="text-[8px] text-[#707973]">Running RF model on {cells.length || "~73"} terrain cells</p>
            </div>
          </div>
        </div>
      ) : cells.length === 0 ? (
        <div className="p-3 text-center">
          <p className="text-[9px] text-[#707973]">No cell data available. Select Sohra on the map.</p>
        </div>
      ) : (
        <>
          {/* What this means */}
          <div className="border-b border-[#e4e3db] bg-[#f8f7f3] px-3 py-2">
            <div className="flex items-start gap-2">
              <span className="mt-0.5 text-[#04442f]">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                  <circle cx="6" cy="6" r="5" stroke="currentColor" strokeWidth="1"/>
                  <path d="M6 5v3M6 3.5v0" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
                </svg>
              </span>
              <p className="text-[8px] leading-relaxed text-[#404943]">
                <span className="font-bold text-[#04442f]">What you're seeing:</span> Instead of one risk score for the entire zone, we run the Random Forest model on each 400m terrain cell. This reveals <span className="font-bold">where risk is concentrated</span> within the zone — some cells may be stable while others are critical.
              </p>
            </div>
          </div>

          {/* Risk Statistics */}
          <div className="px-3 pt-2 pb-1">
            <p className="mb-1.5 text-[8px] font-bold uppercase tracking-wider text-[#707973]">
              Risk Statistics Across {cells.length} Cells
            </p>
            <RiskStats cells={cells} />
          </div>

          {/* State Distribution */}
          <div className="px-3 py-2">
            <p className="mb-1.5 text-[8px] font-bold uppercase tracking-wider text-[#707973]">
              Cell State Breakdown
            </p>
            <StateDistribution cells={cells} />
          </div>

          {/* Mini Heatmap */}
          <div className="px-3 pb-2">
            <p className="mb-1.5 text-[8px] font-bold uppercase tracking-wider text-[#707973]">
              Risk Surface Visualization
            </p>
            <MiniHeatmap cells={cells} />
          </div>

          {/* Expandable cell list */}
          <div className="border-t border-[#e4e3db]">
            <button
              onClick={() => setExpanded(!expanded)}
              className="w-full px-3 py-1.5 flex items-center justify-between text-[8px] font-bold text-[#707973] hover:bg-[#f8f7f3] transition-colors"
            >
              <span>{expanded ? "HIDE" : "SHOW"} CELL DETAILS ({cells.length} cells)</span>
              <svg width="8" height="6" viewBox="0 0 8 6" className={`transition-transform ${expanded ? "rotate-180" : ""}`}>
                <path d="M1 1l3 3 3-3" stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinecap="round"/>
              </svg>
            </button>
            {expanded && (
              <div className="max-h-40 overflow-y-auto border-t border-[#e4e3db]">
                <table className="w-full text-[7px]">
                  <thead className="sticky top-0 bg-[#f8f7f3]">
                    <tr className="text-left text-[#707973]">
                      <th className="px-2 py-1 font-bold">#</th>
                      <th className="px-2 py-1 font-bold">Risk</th>
                      <th className="px-2 py-1 font-bold">State</th>
                      <th className="px-2 py-1 font-bold">Stress</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cells.map((cell, i) => (
                      <tr key={i} className="border-t border-[#e4e3db]">
                        <td className="px-2 py-0.5 text-[#707973]">{i + 1}</td>
                        <td className="px-2 py-0.5 font-bold" style={{ color: cell.slope_state_color }}>
                          {(cell.risk_score * 100).toFixed(1)}%
                        </td>
                        <td className="px-2 py-0.5">
                          <span className="rounded px-1 py-0.5 text-[6px] font-bold text-white"
                            style={{ backgroundColor: cell.slope_state_color }}>
                            {cell.slope_state.slice(0, 3)}
                          </span>
                        </td>
                        <td className="px-2 py-0.5 text-[#707973]">{(cell.stress_score * 100).toFixed(0)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Footer note */}
          <div className="border-t border-[#e4e3db] bg-[#f8f7f3] px-3 py-1.5">
            <p className="text-[7px] text-[#707973]">
              Architecture: Zone-level scoring (remaining 7 zones) extends directly to per-cell with more processing time.
            </p>
          </div>
        </>
      )}
    </div>
  );
}

/* =========================================================
   RISK STATISTICS
========================================================= */

function RiskStats({ cells }: { cells: CellData[] }) {
  const riskScores = cells.map((c) => c.risk_score);
  const avg = riskScores.reduce((a, b) => a + b, 0) / riskScores.length;
  const max = Math.max(...riskScores);
  const min = Math.min(...riskScores);
  const stdDev = Math.sqrt(riskScores.reduce((sum, r) => sum + (r - avg) ** 2, 0) / riskScores.length);
  const median = [...riskScores].sort((a, b) => a - b)[Math.floor(riskScores.length / 2)];

  const stats = [
    { label: "AVERAGE", value: avg, color: "#04442f" },
    { label: "MEDIAN", value: median, color: "#04442f" },
    { label: "MAX", value: max, color: "#ba1a1a" },
    { label: "MIN", value: min, color: "#245c45" },
    { label: "SPREAD", value: stdDev, color: "#d97706" },
  ];

  return (
    <div className="grid grid-cols-5 gap-1">
      {stats.map((s) => (
        <div key={s.label} className="rounded border border-[#e4e3db] p-1.5 text-center">
          <p className="text-[6px] font-bold tracking-wider text-[#707973]">{s.label}</p>
          <p className="text-[11px] font-bold" style={{ color: s.color }}>
            {(s.value * 100).toFixed(1)}%
          </p>
        </div>
      ))}
    </div>
  );
}

/* =========================================================
   STATE DISTRIBUTION
========================================================= */

function StateDistribution({ cells }: { cells: CellData[] }) {
  const stateCounts = cells.reduce((acc, c) => {
    acc[c.slope_state] = (acc[c.slope_state] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const total = cells.length;

  return (
    <div className="space-y-1.5">
      {["CRITICAL", "DEGRADING", "STRESSED", "STABLE"].map((state) => {
        const count = stateCounts[state] || 0;
        const pct = total > 0 ? (count / total) * 100 : 0;
        const color = STATE_COLORS[state];

        return (
          <div key={state} className="flex items-center gap-2">
            <div className="flex items-center gap-1 w-20">
              <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: color }} />
              <span className="text-[8px] font-bold" style={{ color }}>{state}</span>
            </div>
            <div className="h-3 flex-1 rounded-full bg-[#e4e3db] overflow-hidden">
              <div
                className="h-3 rounded-full transition-all duration-500"
                style={{ width: `${pct}%`, backgroundColor: color }}
              />
            </div>
            <div className="w-16 text-right">
              <span className="text-[9px] font-bold text-[#1b1c17]">{count}</span>
              <span className="text-[7px] text-[#707973]"> ({pct.toFixed(0)}%)</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* =========================================================
   MINI HEATMAP
========================================================= */

function MiniHeatmap({ cells }: { cells: CellData[] }) {
  if (cells.length === 0) return null;

  // Find bounds
  const lats = cells.map((c) => c.lat);
  const lngs = cells.map((c) => c.lng);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLng = Math.min(...lngs);
  const maxLng = Math.max(...lngs);
  const latRange = maxLat - minLat || 0.01;
  void minLng; void maxLng; // used for bounds only

  // Grid dimensions
  const cols = Math.ceil(Math.sqrt(cells.length));
  const rows = Math.ceil(cells.length / cols);

  // Sort cells by position for consistent layout
  const sorted = [...cells].sort((a, b) => {
    const rowA = Math.floor(((a.lat - minLat) / latRange) * (rows - 1));
    const rowB = Math.floor(((b.lat - minLat) / latRange) * (rows - 1));
    if (rowA !== rowB) return rowB - rowA; // top to bottom
    return a.lng - b.lng; // left to right
  });

  const maxRisk = Math.max(...cells.map((c) => c.risk_score), 0.01);

  return (
    <div className="rounded border border-[#e4e3db] bg-[#f8f7f3] p-2">
      <div className="grid gap-0.5" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
        {sorted.map((cell, i) => {
          const intensity = cell.risk_score / maxRisk;
          return (
            <div
              key={i}
              className="aspect-square rounded-sm transition-all duration-300 hover:ring-1 hover:ring-[#1b1c17]"
              style={{
                backgroundColor: cell.slope_state_color,
                opacity: 0.3 + intensity * 0.7,
              }}
              title={`Cell ${i + 1}: ${(cell.risk_score * 100).toFixed(1)}% — ${cell.slope_state}`}
            />
          );
        })}
      </div>
      <div className="mt-1.5 flex items-center justify-between">
        <div className="flex items-center gap-1">
          <div className="h-2 w-6 rounded-sm" style={{ backgroundColor: "#245c45", opacity: 0.4 }} />
          <span className="text-[6px] text-[#707973]">Low</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="h-2 w-6 rounded-sm" style={{ backgroundColor: "#d97706", opacity: 0.7 }} />
          <span className="text-[6px] text-[#707973]">Medium</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="h-2 w-6 rounded-sm" style={{ backgroundColor: "#ba1a1a", opacity: 1 }} />
          <span className="text-[6px] text-[#707973]">High</span>
        </div>
      </div>
      <p className="mt-1 text-[6px] text-[#707973] text-center">
        Each square = one 400m terrain cell. Darker = higher risk.
      </p>
    </div>
  );
}

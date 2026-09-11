import { useState, useCallback, useRef, useEffect } from "react";
import { postScenarioSimulation } from "../../api/risk";
import { useUIStore } from "../../store/uiStore";
import type { SimulationResult } from "../../types/risk";

const MULTIPLIER_PRESETS = [
  { label: "Current", value: 1.0 },
  { label: "+25%", value: 1.25 },
  { label: "+50%", value: 1.5 },
  { label: "+75%", value: 1.75 },
  { label: "Extreme", value: 2.0 },
];

const CONTINUED_PRESETS = [
  { label: "NOW", value: 0 },
  { label: "+6H", value: 6 },
  { label: "+12H", value: 12 },
  { label: "+24H", value: 24 },
];

export default function RainfallScenarioControl({ onResults }: { onResults?: (results: SimulationResult[]) => void }) {
  const [multiplier, setMultiplier] = useState(1.0);
  const [continued, setContinued] = useState(0);
  const [results, setResults] = useState<SimulationResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [warning, setWarning] = useState("");
  const [dragging, setDragging] = useState(false);
  const simTime = useUIStore((s) => s.simTime);
  const selectZone = useUIStore((s) => s.selectZone);
  const debounceRef = useRef<number | null>(null);

  // Debounced simulation on slider drag — updates map colors in real-time
  const fireSimulation = useCallback((mult: number, cont: number) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(() => {
      setLoading(true);
      postScenarioSimulation({ multiplier: mult, continued_hours: cont, t: simTime })
        .then((r) => {
          setResults(r.results);
          setWarning(r.warning);
          onResults?.(r.results);
        })
        .catch(() => {})
        .finally(() => setLoading(false));
    }, 150); // 150ms debounce for smooth drag
  }, [simTime, onResults]);

  useEffect(() => () => { if (debounceRef.current) clearTimeout(debounceRef.current); }, []);

  const handleSliderChange = (val: number) => {
    setMultiplier(val);
    setDragging(true);
    fireSimulation(val, continued);
  };

  const handleSliderRelease = () => {
    setDragging(false);
  };

  const runSimulation = useCallback(() => {
    setLoading(true);
    postScenarioSimulation({ multiplier, continued_hours: continued, t: simTime })
      .then((r) => {
        setResults(r.results);
        setWarning(r.warning);
        onResults?.(r.results);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [multiplier, continued, simTime, onResults]);

  // Zone-level risk summary
  const escalatedCount = results?.filter((r) => r.escalated).length ?? 0;
  const maxRisk = results ? Math.max(...results.map((r) => r.simulated_risk)) : 0;

  return (
    <div className="rounded bg-white p-3 shadow-sm">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-[10px] font-bold uppercase tracking-wide text-[#1b1c17]">
          Rainfall Scenario
        </h3>
        <span className="rounded bg-[#d97706]/10 px-1.5 py-0.5 text-[7px] font-bold text-[#92400e]">
          WHAT-IF SIMULATION
        </span>
      </div>

      {/* Rainfall multiplier slider */}
      <div className="mb-2">
        <div className="mb-1 flex justify-between text-[8px] text-[#707973]">
          <span>Current</span>
          <span className={`font-bold ${multiplier > 1.5 ? "text-[#ba1a1a]" : multiplier > 1.25 ? "text-[#ea580c]" : "text-[#1b1c17]"}`}>
            {multiplier === 1.0 ? "Current" : `+${((multiplier - 1) * 100).toFixed(0)}%`}
          </span>
          <span>Extreme</span>
        </div>
        <input
          type="range"
          min={1.0}
          max={2.0}
          step={0.05}
          value={multiplier}
          onChange={(e) => handleSliderChange(Number(e.target.value))}
          onMouseUp={handleSliderRelease}
          onTouchEnd={handleSliderRelease}
          className="w-full accent-[#04442f]"
        />
        <div className="mt-1 flex gap-1">
          {MULTIPLIER_PRESETS.map((p) => (
            <button
              key={p.value}
              onClick={() => { setMultiplier(p.value); fireSimulation(p.value, continued); }}
              className={`flex-1 rounded py-0.5 text-[8px] font-bold ${
                multiplier === p.value
                  ? "bg-[#04442f] text-white"
                  : "bg-[#f0eee6] text-[#404943] hover:bg-[#d9e2d9]"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Continued rainfall */}
      <div className="mb-2">
        <p className="mb-1 text-[8px] font-bold text-[#707973]">CONTINUED RAINFALL</p>
        <div className="flex gap-1">
          {CONTINUED_PRESETS.map((p) => (
            <button
              key={p.value}
              onClick={() => { setContinued(p.value); fireSimulation(multiplier, p.value); }}
              className={`flex-1 rounded py-1 text-[9px] font-bold ${
                continued === p.value
                  ? "bg-[#04442f] text-white"
                  : "bg-[#f0eee6] text-[#404943] hover:bg-[#d9e2d9]"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Run button */}
      <button
        onClick={runSimulation}
        disabled={loading}
        className="w-full rounded bg-[#04442f] py-1.5 text-[10px] font-bold text-white hover:bg-[#0a5c40] disabled:opacity-50"
      >
        {loading ? "SIMULATING..." : "RUN SCENARIO"}
      </button>

      {/* Quick summary when dragging */}
      {dragging && results && (
        <div className="mt-2 flex items-center gap-2 rounded border border-[#d97706] bg-[#d97706]/5 p-1.5">
          <span className="text-[8px] font-bold text-[#92400e]">PREVIEW</span>
          <span className="text-[9px] text-[#404943]">
            Max risk: <span className="font-bold" style={{ color: maxRisk > 0.75 ? "#ba1a1a" : maxRisk > 0.5 ? "#ea580c" : "#d97706" }}>
              {(maxRisk * 100).toFixed(0)}%
            </span>
          </span>
          {escalatedCount > 0 && (
            <span className="text-[8px] font-bold text-[#ba1a1a]">
              {escalatedCount} ESC
            </span>
          )}
        </div>
      )}

      {/* Results */}
      {results && !dragging && (
        <div className="mt-2 space-y-1.5">
          <p className="text-[8px] font-bold text-[#92400e]">{warning}</p>

          {results.slice(0, 5).map((r) => {
            const riskChange = r.simulated_risk - r.current_risk;
            const changed = Math.abs(riskChange) > 0.01;

            return (
              <button
                key={r.zone_id}
                onClick={() => selectZone(r.zone_id)}
                className="w-full rounded border border-[#e4e3db] p-1.5 text-left hover:border-[#04442f]/30"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[9px] font-bold text-[#1b1c17]">{r.name}</span>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[9px] text-[#707973]">
                      {(r.current_risk * 100).toFixed(0)}%
                    </span>
                    {changed && (
                      <>
                        <span className="text-[8px] text-[#707973]">&rarr;</span>
                        <span
                          className="text-[9px] font-bold"
                          style={{ color: r.slope_state_color }}
                        >
                          {(r.simulated_risk * 100).toFixed(0)}%
                        </span>
                      </>
                    )}
                  </div>
                </div>
                <div className="mt-0.5 flex items-center gap-1">
                  <span
                    className="rounded px-1 py-0.5 text-[7px] font-bold text-white"
                    style={{ backgroundColor: r.slope_state_color }}
                  >
                    {r.slope_state_label}
                  </span>
                  {r.escalated && (
                    <span className="rounded bg-[#ba1a1a]/10 px-1 py-0.5 text-[7px] font-bold text-[#ba1a1a]">
                      ESC
                    </span>
                  )}
                </div>
              </button>
            );
          })}

          {results.length > 5 && (
            <p className="text-[8px] text-[#707973]">+{results.length - 5} additional zones</p>
          )}
        </div>
      )}
    </div>
  );
}

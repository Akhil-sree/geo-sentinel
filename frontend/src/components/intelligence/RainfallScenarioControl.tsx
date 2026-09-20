import { useState, useCallback } from "react";
import { postScenarioSimulation } from "../../api/risk";
import { useUIStore } from "../../store/uiStore";
import { fmtPctOpt } from "../../lib/format";
import type { SimulationResult } from "../../types/risk";

const MULTIPLIER_PRESETS = [
  { label: "Current", value: 1.0 },
  { label: "+25%", value: 1.25 },
  { label: "+50%", value: 1.5 },
  { label: "+75%", value: 1.75 },
  { label: "Extreme", value: 2.0 },
];

const CONTINUED_PRESETS = [
  { label: "Now", value: 0 },
  { label: "+6h", value: 6 },
  { label: "+12h", value: 12 },
  { label: "+24h", value: 24 },
];

export default function RainfallScenarioControl({ onResults, onClear }: {
  onResults?: (results: SimulationResult[], label: string) => void;
  onClear?: () => void;
}) {
  const [multiplier, setMultiplier] = useState(1.0);
  const [continued, setContinued] = useState(0);
  const [results, setResults] = useState<SimulationResult[] | null>(null);
  const [scenarioLabel, setScenarioLabel] = useState("");
  const [loading, setLoading] = useState(false);
  const [warning, setWarning] = useState("");
  const [error, setError] = useState<string | null>(null);
  const simTime = useUIStore((s) => s.simTime);
  const selectZone = useUIStore((s) => s.selectZone);

  const runSimulation = useCallback(() => {
    setLoading(true);
    setError(null);
    postScenarioSimulation({ multiplier, continued_hours: continued, t: simTime })
      .then((r) => {
        setResults(r.results);
        setScenarioLabel(r.scenario?.label ?? "");
        setWarning(r.warning);
        onResults?.(r.results, r.scenario?.label ?? "");
      })
      .catch(() => setError("Scenario service unreachable — is the backend running?"))
      .finally(() => setLoading(false));
  }, [multiplier, continued, simTime, onResults]);

  const clear = useCallback(() => {
    setResults(null);
    setWarning("");
    setScenarioLabel("");
    setError(null);
    onClear?.();
  }, [onClear]);

  return (
    <div className="rounded-card p-5" style={{
      background: 'rgba(255, 255, 255, 0.58)',
      backdropFilter: 'blur(5px)',
      WebkitBackdropFilter: 'blur(5px)',
      border: '1px solid rgba(255, 255, 255, 0.32)',
      boxShadow: '0 2px 10px rgba(15, 35, 27, 0.04)',
    }}>
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-[20px] font-bold text-gs-text tracking-tight">
          RAINFALL SCENARIO
        </h3>
        <span className="rounded-md bg-risk-stressed/10 px-3 py-1 text-[13px] font-semibold text-risk-stressed ring-1 ring-risk-stressed/20">
          What-if simulation
        </span>
      </div>

      {/* Rainfall multiplier slider */}
      <div className="mb-5">
        <div className="mb-2 flex justify-between text-[14px] text-gs-text-secondary">
          <span>Current</span>
          <span className="font-semibold text-gs-text">
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
          onChange={(e) => setMultiplier(Number(e.target.value))}
          className="w-full accent-forest"
        />
        <div className="mt-3 flex gap-2">
          {MULTIPLIER_PRESETS.map((p) => (
            <button
              key={p.value}
              onClick={() => setMultiplier(p.value)}
              className={`flex-1 rounded-md py-2 text-[13px] font-semibold transition ${
                multiplier === p.value
                  ? "bg-forest text-white"
                  : "bg-gs-surface-soft text-gs-text-secondary hover:bg-gs-border/50"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Continued rainfall */}
      <div className="mb-5">
        <p className="mb-2 text-[14px] font-medium text-gs-text-secondary">Continued rainfall</p>
        <div className="flex gap-2">
          {CONTINUED_PRESETS.map((p) => (
            <button
              key={p.value}
              onClick={() => setContinued(p.value)}
              className={`flex-1 rounded-md py-2.5 text-[14px] font-semibold transition ${
                continued === p.value
                  ? "bg-forest text-white"
                  : "bg-gs-surface-soft text-gs-text-secondary hover:bg-gs-border/50"
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
        className="w-full rounded-card bg-forest py-3.5 text-[15px] font-semibold text-white transition hover:bg-forest-800 disabled:opacity-50 active:scale-[0.98]"
      >
        {loading ? "Simulating…" : "Run scenario"}
      </button>
      {error && (
        <p className="mt-2 text-[13px] font-medium text-risk-critical">{error}</p>
      )}

      {/* Results */}
      {results && (
        <div className="mt-5 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-[14px] font-medium text-risk-stressed">
              {scenarioLabel ? `${scenarioLabel} — ` : ""}{warning}
            </p>
            <button
              onClick={clear}
              className="shrink-0 rounded-md px-2 py-1 text-[12px] font-semibold text-gs-text-secondary transition hover:bg-gs-border/50"
            >
              ✕ Clear
            </button>
          </div>

          {results.slice(0, 5).map((r) => {
            const riskChange = r.simulated_risk - r.current_risk;
            const changed = Math.abs(riskChange) > 0.01;

            return (
              <button
                key={r.zone_id}
                onClick={() => selectZone(r.zone_id)}
                className="w-full rounded-card border border-gs-border p-4 text-left hover:shadow-card-hover transition-all"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[16px] font-semibold text-gs-text">{r.name}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-[14px] text-gs-text-secondary">
                      {fmtPctOpt(r.current_risk)}
                    </span>
                    {changed && (
                      <>
                        <span className="text-[13px] text-gs-text-secondary">→</span>
                        <span
                          className="text-[16px] font-bold"
                          style={{ color: r.slope_state_color }}
                        >
                          {fmtPctOpt(r.simulated_risk)}
                        </span>
                      </>
                    )}
                  </div>
                </div>
                <div className="mt-2.5 flex items-center gap-2">
                  <span
                    className="rounded-md px-2.5 py-1 text-[12px] font-semibold text-white"
                    style={{ backgroundColor: r.slope_state_color }}
                  >
                    {r.slope_state_label}
                  </span>
                  {r.escalated && (
                    <span className="rounded-md bg-risk-critical/10 px-2.5 py-1 text-[12px] font-semibold text-risk-critical">
                      Escalated
                    </span>
                  )}
                </div>
              </button>
            );
          })}

          {results.length > 5 && (
            <p className="text-[13px] text-gs-text-secondary">+{results.length - 5} additional zones</p>
          )}
        </div>
      )}
    </div>
  );
}

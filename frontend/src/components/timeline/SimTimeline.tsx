import { useSimClock } from "../../hooks/useSimClock";
import PhaseBadge from "./PhaseBadge";

const MIN_T = 24, MAX_T = 168;

const label = (t: number) => {
  const day = 14 + Math.floor(t / 24), hr = t % 24;
  return `2026-07-${String(day).padStart(2, "0")} ${String(hr).padStart(2, "0")}:00`;
};

export default function SimTimeline() {
  const { simTime, playing, setSimTime, togglePlay, step } = useSimClock();

  return (
    <div className="absolute bottom-4 left-1/2 w-[560px] -translate-x-1/2
                    rounded border border-slate-700 bg-[#0d1526]/95 px-4 py-2.5">
      <div className="mb-1 flex items-center justify-between">
        <button onClick={togglePlay}
          className="rounded bg-sky-700 px-3 py-1 text-xs font-bold">
          {playing ? "⏸ PAUSE" : "▶ PLAY EVENT"}
        </button>
        <PhaseBadge t={simTime} />
        <span className="font-mono text-xs text-slate-300">{label(simTime)}</span>
        <span className="flex gap-1">
          <button onClick={() => step(-6)} className="rounded bg-slate-800 px-2 text-xs">−6h</button>
          <button onClick={() => step(6)} className="rounded bg-slate-800 px-2 text-xs">+6h</button>
        </span>
      </div>
      <input type="range" min={MIN_T} max={MAX_T} value={simTime} step={1}
        onChange={(e) => setSimTime(Number(e.target.value))} className="w-full" />
      <p className="mt-0.5 text-[9px] text-slate-500">
        Demo event scrubber — every position recomputes the full pipeline server-side, never interpolated in the browser
      </p>
    </div>
  );
}

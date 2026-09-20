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
    <div className="absolute bottom-4 left-1/2 w-[540px] -translate-x-1/2
                    rounded-card px-4 py-2.5" style={{
      background: 'rgba(6, 22, 17, 0.82)',
      backdropFilter: 'blur(14px)',
      WebkitBackdropFilter: 'blur(14px)',
      border: '1px solid rgba(255, 255, 255, 0.10)',
      boxShadow: '0 8px 30px rgba(0, 0, 0, 0.30)',
    }}>
      <div className="mb-1.5 flex items-center justify-between">
        <button onClick={togglePlay}
          className="rounded bg-forest px-3 py-1 text-[10px] font-semibold text-white transition hover:bg-forest-800">
          {playing ? "⏸ Pause" : "▶ Play event"}
        </button>
        <PhaseBadge t={simTime} />
        <span className="font-mono text-[10px] text-white/60">{label(simTime)}</span>
        <span className="flex gap-1">
          <button onClick={() => step(-6)} className="rounded bg-white/10 px-2 py-0.5 text-[10px] text-white/70 transition hover:bg-white/20">−6h</button>
          <button onClick={() => step(6)} className="rounded bg-white/10 px-2 py-0.5 text-[10px] text-white/70 transition hover:bg-white/20">+6h</button>
        </span>
      </div>
      <input type="range" min={MIN_T} max={MAX_T} value={simTime} step={1}
        onChange={(e) => setSimTime(Number(e.target.value))} className="w-full" />
      <p className="mt-1 text-[8px] text-white/40">
        Event scrubber — every position recomputes the full pipeline server-side, never interpolated
      </p>
    </div>
  );
}

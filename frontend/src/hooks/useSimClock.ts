import { useEffect } from "react";
import { useUIStore } from "../store/uiStore";

const MIN_T = 24, MAX_T = 168, STEP_H = 1, INTERVAL_MS = 400;

export function useSimClock() {
  const { simTime, playing, setSimTime, togglePlay } = useUIStore();

  useEffect(() => {
    if (!playing) return;
    const iv = setInterval(() => {
      const t = useUIStore.getState().simTime;
      if (t >= MAX_T) { useUIStore.setState({ playing: false }); return; }
      setSimTime(t + STEP_H);
    }, INTERVAL_MS);
    return () => clearInterval(iv);
  }, [playing, setSimTime]);

  return { simTime, playing, setSimTime, togglePlay,
           step: (d: number) => setSimTime(Math.min(MAX_T, Math.max(MIN_T, simTime + d))) };
}

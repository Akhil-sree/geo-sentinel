import { create } from "zustand";

interface UIState {
  simTime: number;          // hours 24..168 on the scrubber
  playing: boolean;
  selectedZoneId: string | null;
  lowBandwidth: boolean;
  setSimTime: (t: number) => void;
  togglePlay: () => void;
  selectZone: (id: string | null) => void;
  toggleLowBandwidth: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  simTime: 96,
  playing: false,
  selectedZoneId: null,
  lowBandwidth: (() => {
    try { return localStorage.getItem("gs_low_bw") === "true"; } catch { return false; }
  })(),
  setSimTime: (t) => set({ simTime: t }),
  togglePlay: () => set((s) => ({ playing: !s.playing })),
  selectZone: (id) => set({ selectedZoneId: id }),
  toggleLowBandwidth: () => set((s) => {
    const next = !s.lowBandwidth;
    try { localStorage.setItem("gs_low_bw", String(next)); } catch {}
    return { lowBandwidth: next };
  }),
}));

import { create } from "zustand";

interface UIState {
  simTime: number;          // hours 24..168 on the scrubber
  playing: boolean;
  selectedZoneId: string | null;
  setSimTime: (t: number) => void;
  togglePlay: () => void;
  selectZone: (id: string | null) => void;
}

export const useUIStore = create<UIState>((set) => ({
  simTime: 96,
  playing: false,
  selectedZoneId: null,
  setSimTime: (t) => set({ simTime: t }),
  togglePlay: () => set((s) => ({ playing: !s.playing })),
  selectZone: (id) => set({ selectedZoneId: id }),
}));

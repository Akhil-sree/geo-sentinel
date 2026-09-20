import { create } from "zustand";
import type { RescueRouteResult } from "../api/dashboard";

export type RescueStatus = "idle" | "calculating" | "success" | "unavailable" | "error";
export type JourneyPhase = "idle" | "running" | "paused" | "done";

interface UIState {
  simTime: number;          // hours 24..168 on the scrubber
  playing: boolean;
  selectedZoneId: string | null;
  setSimTime: (t: number) => void;
  togglePlay: () => void;
  selectZone: (id: string | null) => void;

  // ── Rescue navigation: single source of truth (§14) ──
  // Panel, map layer and floating chip all consume this same object.
  rescueRoute: RescueRouteResult | null;
  rescueStatus: RescueStatus;
  journeyPhase: JourneyPhase;
  journeyStep: number; // index into route geometry coordinates
  setRescueRoute: (route: RescueRouteResult | null, status: RescueStatus) => void;
  clearRescueRoute: () => void;
  setJourneyPhase: (phase: JourneyPhase) => void;
  setJourneyStep: (step: number) => void;
  resetJourney: () => void;
  // Map → panel handoff: SafeZoneLayer click requests an explicit
  // recalculation to that safe zone; the panel consumes + clears it.
  safeZoneRequest: { safeId: string; lat: number; lng: number; name: string } | null;
  setSafeZoneRequest: (r: { safeId: string; lat: number; lng: number; name: string } | null) => void;
}

export const useUIStore = create<UIState>((set) => ({
  simTime: 96,
  playing: false,
  selectedZoneId: null,
  setSimTime: (t) => set({ simTime: t }),
  togglePlay: () => set((s) => ({ playing: !s.playing })),
  selectZone: (id) => set({ selectedZoneId: id, rescueRoute: null, rescueStatus: "idle", journeyPhase: "idle", journeyStep: 0, safeZoneRequest: null }),

  rescueRoute: null,
  rescueStatus: "idle",
  journeyPhase: "idle",
  journeyStep: 0,
  setRescueRoute: (route, status) => set({
    rescueRoute: route,
    rescueStatus: status,
    journeyPhase: "idle",
    journeyStep: 0,
  }),
  clearRescueRoute: () => set({
    rescueRoute: null,
    rescueStatus: "idle",
    journeyPhase: "idle",
    journeyStep: 0,
  }),
  setJourneyPhase: (phase) => set({ journeyPhase: phase }),
  setJourneyStep: (step) => set({ journeyStep: step }),
  resetJourney: () => set({ journeyPhase: "idle", journeyStep: 0 }),
  safeZoneRequest: null,
  setSafeZoneRequest: (r) => set({ safeZoneRequest: r }),
}));

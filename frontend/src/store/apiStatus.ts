import { create } from "zustand";

export type BackendState = "unknown" | "online" | "degraded" | "offline";

/**
 * Global backend-connectivity store — the shared answer to
 * "is this empty screen NO DATA or SYSTEM FAILURE?".
 *
 * Fed by the axios interceptor in api/client.ts:
 * - any HTTP response (even 4xx/5xx) proves the backend is reachable
 * - a response-less network error (timeout/DNS/refused) proves it is not
 * - repeated 5xx responses mark it degraded (reachable but failing)
 *
 * Components keep their local empty-states for genuine "no data";
 * the BackendStatusBanner renders the system-failure state globally.
 */
interface ApiStatusState {
  backend: BackendState;
  consecutiveFailures: number;
  lastErrorAt: string | null;
  lastErrorUrl: string | null;
  reportSuccess: () => void;
  reportFailure: (info: { url?: string; status?: number }) => void;
  reset: () => void;
}

export const useApiStatus = create<ApiStatusState>((set) => ({
  backend: "unknown",
  consecutiveFailures: 0,
  lastErrorAt: null,
  lastErrorUrl: null,

  reportSuccess: () =>
    set({
      backend: "online",
      consecutiveFailures: 0,
      lastErrorAt: null,
      lastErrorUrl: null,
    }),

  reportFailure: ({ url, status }) =>
    set((s) => {
      const failures = s.consecutiveFailures + 1;
      // No HTTP response at all (timeout/DNS/refused) = unreachable.
      // A 5xx response proves reachability — the backend is up but failing.
      const offline = status === undefined || status === 0;
      return {
        consecutiveFailures: failures,
        lastErrorAt: new Date().toISOString(),
        lastErrorUrl: url ?? s.lastErrorUrl,
        backend: offline ? "offline" : "degraded",
      };
    }),

  reset: () =>
    set({
      backend: "unknown",
      consecutiveFailures: 0,
      lastErrorAt: null,
      lastErrorUrl: null,
    }),
}));

export function backendLabel(s: BackendState): string {
  switch (s) {
    case "online":
      return "BACKEND ONLINE";
    case "degraded":
      return "BACKEND DEGRADED";
    case "offline":
      return "BACKEND UNAVAILABLE";
    default:
      return "BACKEND STATUS UNKNOWN";
  }
}

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { routeCoordsToLatLngs, routeLatLngs } from "../components/map/RescueRouteLayer";
import { useUIStore } from "../store/uiStore";
import RescueRoutePanel from "../components/intelligence/RescueRoutePanel";
import type { RescueRouteResult } from "../api/dashboard";

vi.mock("../api/dashboard", async (importOriginal) => {
  const mod = await importOriginal<typeof import("../api/dashboard")>();
  return { ...mod, getRescueRoute: vi.fn(), getSafeZones: vi.fn() };
});

import { getRescueRoute } from "../api/dashboard";

const ZONES = [
  { id: "Z1", name: "Sohra (Cherrapunji)", lat: 25.3, lng: 91.7 },
  { id: "Z3", name: "Shillong North Slopes", lat: 25.62, lng: 91.9 },
];

const API_GEOM = [[91.57, 25.29], [91.58, 25.31], [91.9, 25.62]];

const OK_ROUTE: RescueRouteResult = {
  status: "ok",
  route_available: true,
  origin: { lat: 25.3, lng: 91.7 },
  destination: { lat: 25.62, lng: 91.9 },
  algorithm: "A* (distance-optimal)",
  geometry: { type: "LineString", coordinates: API_GEOM },
  route_geometry: [[25.29, 91.57], [25.31, 91.58], [25.62, 91.9]],
  distance_km: 42.47,
  eta_min: 64,
  segments: [{ road_id: 1, name: "Test Road", length_m: 1000, status: "OPEN" }],
  blocked_avoided: [],
  road_count: 1,
  explanation: { why: ["A* road-network search over OSM geometry"], tradeoffs: [] },
};

beforeEach(() => {
  cleanup();
  useUIStore.getState().clearRescueRoute();
  useUIStore.getState().selectZone(null);
  vi.resetAllMocks();
});

afterEach(() => {
  cleanup();
});

describe("§27 API route_geometry == map geometry", () => {
  it("conversion preserves values, order and count — format change only", () => {
    const out = routeCoordsToLatLngs(API_GEOM);
    expect(out).toHaveLength(API_GEOM.length);
    expect(out).toEqual([[25.29, 91.57], [25.31, 91.58], [25.62, 91.9]]);
    // every backend point survives, none added, none reordered
    API_GEOM.forEach(([lng, lat], i) => {
      expect(out[i][0]).toBe(lat);
      expect(out[i][1]).toBe(lng);
    });
  });
});

describe("rescue store: single source of truth", () => {
  it("setRescueRoute stores the SAME object the panel received", () => {
    useUIStore.getState().setRescueRoute(OK_ROUTE, "success");
    const s = useUIStore.getState();
    expect(s.rescueRoute).toBe(OK_ROUTE);
    expect(s.rescueStatus).toBe("success");
    expect(s.journeyPhase).toBe("idle");
    expect(s.journeyStep).toBe(0);
  });
  it("journey transitions + clear reset everything (no stale geometry)", () => {
    const st = useUIStore.getState();
    st.setRescueRoute(OK_ROUTE, "success");
    st.setJourneyPhase("running");
    st.setJourneyStep(2);
    expect(useUIStore.getState().journeyPhase).toBe("running");
    st.resetJourney();
    expect(useUIStore.getState().journeyPhase).toBe("idle");
    expect(useUIStore.getState().journeyStep).toBe(0);
    expect(useUIStore.getState().rescueRoute).toBe(OK_ROUTE); // route kept
    st.clearRescueRoute();
    const s = useUIStore.getState();
    expect(s.rescueRoute).toBeNull();
    expect(s.rescueStatus).toBe("idle");
  });
});

describe("RescueRoutePanel states", () => {
  it("success: route card shows backend distance/ETA", async () => {
    vi.mocked(getRescueRoute).mockResolvedValue(OK_ROUTE);
    render(<RescueRoutePanel zones={ZONES} />);
    fireEvent.click(screen.getByText(/FIND LOWER-EXPOSURE ROUTE/));
    await waitFor(() => expect(screen.getByText(/Route found/)).toBeTruthy());
    expect(screen.getByText("42.47 km")).toBeTruthy();
    expect(useUIStore.getState().rescueRoute?.geometry.coordinates).toBe(API_GEOM);
  });
  it("unavailable: message + no geometry drawn", async () => {
    vi.mocked(getRescueRoute).mockResolvedValue({
      ...OK_ROUTE, route_available: false, geometry: { type: "LineString", coordinates: [] },
      distance_km: 0, explanation: { why: ["No connected road path"], tradeoffs: [] },
    });
    render(<RescueRoutePanel zones={ZONES} />);
    fireEvent.click(screen.getByText(/FIND LOWER-EXPOSURE ROUTE/));
    await waitFor(() => expect(screen.getByText(/ROUTE UNAVAILABLE/)).toBeTruthy());
    expect(screen.getByText(/No route has been drawn/)).toBeTruthy();
  });
  it("error: service unavailable, retry possible", async () => {
    vi.mocked(getRescueRoute).mockRejectedValue(new Error("down"));
    render(<RescueRoutePanel zones={ZONES} />);
    fireEvent.click(screen.getByText(/FIND LOWER-EXPOSURE ROUTE/));
    await waitFor(() => expect(screen.getByText(/ROUTING SERVICE UNAVAILABLE/)).toBeTruthy());
  });
  it("same origin/destination blocks the request", () => {
    render(<RescueRoutePanel zones={ZONES} />);
    const selects = screen.getAllByRole("combobox");
    fireEvent.change(selects[1], { target: { value: "Z1" } }); // TO = FROM
    expect(screen.getByText(/must differ/)).toBeTruthy();
    expect(screen.getByText(/FIND LOWER-EXPOSURE ROUTE/).closest("button")?.disabled).toBe(true);
    expect(vi.mocked(getRescueRoute)).not.toHaveBeenCalled();
  });
});

describe("auto safe-route: risk zone click → FIND SAFE ROUTE → map geometry", () => {
  it("posts origin only (backend auto-selects) and stores named route", async () => {
    useUIStore.getState().selectZone("Z1");
    vi.mocked(getRescueRoute).mockResolvedValue(OK_ROUTE);
    render(<RescueRoutePanel zones={ZONES} />);
    fireEvent.click(screen.getByText(/\[ FIND SAFE ROUTE \]/));
    await waitFor(() => expect(screen.getByText(/Route found/)).toBeTruthy());
    // destination omitted → backend auto-select
    expect(vi.mocked(getRescueRoute)).toHaveBeenCalledWith(25.3, 91.7);
    expect(useUIStore.getState().rescueRoute?.originName).toBe("Sohra (Cherrapunji)");
  });
  it("ranked options tap recalculates an explicit route", async () => {
    useUIStore.getState().selectZone("Z1");
    const withOpts: RescueRouteResult = {
      ...OK_ROUTE,
      options: [{ id: "sz-6", name: "Sohra Evacuation Centre", lat: 25.27, lng: 91.73, distance_km: 12.4, eta_min: 19 }],
    };
    vi.mocked(getRescueRoute).mockResolvedValue(withOpts);
    render(<RescueRoutePanel zones={ZONES} />);
    fireEvent.click(screen.getByText(/\[ FIND SAFE ROUTE \]/));
    await waitFor(() => expect(screen.getByText(/Other reachable options/)).toBeTruthy());
    fireEvent.click(screen.getByText(/Sohra Evacuation Centre/));
    await waitFor(() =>
      expect(vi.mocked(getRescueRoute)).toHaveBeenCalledWith(25.3, 91.7, 25.27, 91.73)
    );
  });
  it("REGRESSION §23: success + geometry ⇒ drawable map input (never empty layer)", async () => {
    useUIStore.getState().selectZone("Z1");
    vi.mocked(getRescueRoute).mockResolvedValue(OK_ROUTE);
    render(<RescueRoutePanel zones={ZONES} />);
    fireEvent.click(screen.getByText(/\[ FIND SAFE ROUTE \]/));
    await waitFor(() => expect(useUIStore.getState().rescueStatus).toBe("success"));
    // The exact object the map layer consumes must yield >2 drawable points.
    const latLngs = routeLatLngs(useUIStore.getState().rescueRoute);
    expect(latLngs.length).toBeGreaterThan(2);
  });
  it("selecting another risk zone clears the old route", () => {
    const st = useUIStore.getState();
    st.setRescueRoute(OK_ROUTE, "success");
    st.selectZone("Z3");
    const s = useUIStore.getState();
    expect(s.rescueRoute).toBeNull();
    expect(s.rescueStatus).toBe("idle");
  });
});

describe("routeLatLngs map-input contract", () => {
  it("prefers route_geometry verbatim", () => {
    expect(routeLatLngs(OK_ROUTE)).toEqual([[25.29, 91.57], [25.31, 91.58], [25.62, 91.9]]);
  });
  it("falls back to geometry conversion", () => {
    const { route_geometry, ...legacy } = OK_ROUTE;
    expect(routeLatLngs(legacy)).toEqual([[25.29, 91.57], [25.31, 91.58], [25.62, 91.9]]);
  });
  it("unavailable route yields no drawable points", () => {
    expect(routeLatLngs({ ...OK_ROUTE, route_available: false, route_geometry: [], geometry: { type: "LineString", coordinates: [] } })).toEqual([]);
    expect(routeLatLngs(null)).toEqual([]);
  });
});

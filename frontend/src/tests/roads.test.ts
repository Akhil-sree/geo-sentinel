import { describe, expect, it } from "vitest";
import { haversineKm, snapToRoad, roadClassRadius } from "../lib/roads";

const SEGS = [
  { id: 1, name: "Shillong-Sohra Road", status: "OPEN", road_type: "district", latitude: 25.31, longitude: 91.8 },
  { id: 2, name: "Shillong-Jowai Highway", status: "OPEN", road_type: "national", latitude: 25.53, longitude: 92.05 },
];

describe("haversineKm", () => {
  it("known distance Sohra approx", () => {
    const d = haversineKm(25.3, 91.7, 25.31, 91.8);
    expect(d).toBeGreaterThan(5);
    expect(d).toBeLessThan(15);
  });
});

describe("snapToRoad", () => {
  it("snaps to the nearest REAL midpoint (never an interpolation)", () => {
    const r = snapToRoad(25.3, 91.7, SEGS as never);
    expect(r).not.toBeNull();
    // snapped point IS a real segment midpoint, not a computed average
    expect(r!.snapped).toEqual({ lat: 25.31, lng: 91.8 });
    expect(r!.segment_name).toBe("Shillong-Sohra Road");
    // original preserved verbatim
    expect(r!.original).toEqual({ lat: 25.3, lng: 91.7 });
    expect(r!.road_distance_m).toBeGreaterThan(0);
  });
  it("returns null on invalid input / empty network / no valid segment", () => {
    expect(snapToRoad(999, 0, SEGS as never)).toBeNull();
    expect(snapToRoad(NaN, 91.7, SEGS as never)).toBeNull();
    expect(snapToRoad(25.3, 91.7, [])).toBeNull();
    expect(
      snapToRoad(25.3, 91.7, [{ id: 9, name: "bad", status: "OPEN", latitude: 999, longitude: 0 }] as never),
    ).toBeNull();
  });
  it("distance is geographically plausible", () => {
    const r = snapToRoad(25.31, 91.8, SEGS as never)!;
    expect(r.road_distance_m).toBe(0);
  });
});

describe("roadClassRadius", () => {
  it("reflects real classes only", () => {
    expect(roadClassRadius("national")).toBeGreaterThan(roadClassRadius("district"));
    expect(roadClassRadius("district")).toBeGreaterThan(roadClassRadius("village"));
    expect(roadClassRadius("zzz-unknown")).toBe(4);
  });
});

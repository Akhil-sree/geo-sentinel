import { describe, it, expect } from "vitest";
import { chipFor } from "../components/layout/DataFreshnessBar";

describe("provenance chips never overclaim", () => {
  it("marks verified providers LIVE", () => {
    const c = chipFor({
      source: "rainfall", freshness: "LIVE", quality: "LIVE",
      is_live: true, is_simulated: false,
      observed_at: new Date().toISOString(),
    });
    expect(c.name).toContain("LIVE");
    expect(c.color).toBe("#1FAF6B");
  });

  it("marks mocks SIMULATED, never live", () => {
    const c = chipFor({
      source: "rainfall", freshness: "SIMULATED", quality: "DEMO_DATA",
      is_live: false, is_simulated: true, observed_at: null,
    });
    expect(c.name).toContain("SIMULATED");
    expect(c.name).not.toContain("LIVE");
  });

  it("quarantines satellite as DEMO excluded from risk", () => {
    const c = chipFor({
      source: "sentinel1_sar", freshness: "SATELLITE_DEMO",
      quality: "demo", is_live: false, is_simulated: true, observed_at: null,
    });
    expect(c.status).toMatch(/excluded from risk/i);
  });

  it("surfaces stale distinctly", () => {
    const c = chipFor({
      source: "soil_moisture", freshness: "STALE — no recent successful run",
      quality: "x", is_live: false, is_simulated: true, observed_at: null,
    });
    expect(c.name).toContain("STALE");
  });
});

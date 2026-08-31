import { describe, expect, it } from "vitest";
import { SEV_ORDER, atLeast, isAlertEligible } from "../lib/severity";

describe("severity ordering", () => {
  it("orders LOW < MODERATE < HIGH < VERY_HIGH", () => {
    expect(SEV_ORDER).toEqual(["LOW", "MODERATE", "HIGH", "VERY_HIGH"]);
  });

  it("atLeast: HIGH is at least MODERATE but not at least VERY_HIGH", () => {
    expect(atLeast("HIGH", "MODERATE")).toBe(true);
    expect(atLeast("HIGH", "VERY_HIGH")).toBe(false);
    expect(atLeast("LOW", "LOW")).toBe(true);
  });

  it("dispatch gate: only HIGH and VERY_HIGH are eligible", () => {
    expect(isAlertEligible("LOW")).toBe(false);
    expect(isAlertEligible("MODERATE")).toBe(false);
    expect(isAlertEligible("HIGH")).toBe(true);
    expect(isAlertEligible("VERY_HIGH")).toBe(true);
  });
});

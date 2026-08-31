import { describe, expect, it } from "vitest";
import { fmtPct, fmtMm, relativeAge } from "../lib/format";

describe("format", () => {
  it("formats percentages and rainfall", () => {
    expect(fmtPct(0.723)).toBe("72%");
    expect(fmtMm(38.4)).toBe("38 mm");
  });
  it("es relative age", () => {
    const hoursAgo = new Date(Date.now() - 3 * 3.6e6).toISOString();
    expect(relativeAge(hoursAgo)).toBe("3h ago");
  });
});

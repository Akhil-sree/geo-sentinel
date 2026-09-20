import { describe, expect, it } from "vitest";
import { gsDisplayState } from "../api/gs";
import { fmtNum, fmtPctOpt, fmtMmOpt, nullState } from "../lib/format";

describe("gsDisplayState (explicit AVAILABLE/UNAVAILABLE/PROCESSING/ERROR)", () => {
  it("PROCESSING while loading, even with a stale result", () => {
    expect(
      gsDisplayState(true, null, { risk_score: 0.5 } as never),
    ).toBe("PROCESSING");
  });
  it("ERROR when the request failed", () => {
    expect(gsDisplayState(false, "boom", null)).toBe("ERROR");
  });
  it("UNAVAILABLE for null risk_score (never coerced to 0)", () => {
    expect(
      gsDisplayState(false, null, { risk_score: null } as never),
    ).toBe("UNAVAILABLE");
    expect(gsDisplayState(false, null, null)).toBe("UNAVAILABLE");
  });
  it("AVAILABLE only for a finite numeric score", () => {
    expect(
      gsDisplayState(false, null, { risk_score: 0.699 } as never),
    ).toBe("AVAILABLE");
    expect(
      gsDisplayState(false, null, { risk_score: NaN } as never),
    ).toBe("UNAVAILABLE");
  });
});

describe("null-safe formatters (NULL renders as em-dash, never 0/NaN)", () => {
  it("fmtNum", () => {
    expect(fmtNum(0.699)).toBe("0.70");
    expect(fmtNum(null)).toBe("—");
    expect(fmtNum(undefined)).toBe("—");
    expect(fmtNum(NaN)).toBe("—");
  });
  it("fmtPctOpt", () => {
    expect(fmtPctOpt(0.699)).toBe("70%");
    expect(fmtPctOpt(null)).toBe("—");
  });
  it("fmtMmOpt", () => {
    expect(fmtMmOpt(12.4)).toBe("12 mm");
    expect(fmtMmOpt(null)).toBe("—");
  });
  it("nullState", () => {
    expect(nullState(0)).toBe("AVAILABLE");
    expect(nullState(null)).toBe("UNAVAILABLE");
  });
});

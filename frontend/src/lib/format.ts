export const fmtPct = (v: number, digits = 0) => `${(v * 100).toFixed(digits)}%`;

export const fmtMm = (v: number) => `${v.toFixed(0)} mm`;

// Null-safe variants: backend may return null (data unavailable). NULL is
// rendered as "—", never as 0, NaN, or a fake prediction.
type MaybeNum = number | null | undefined;
const isNum = (v: MaybeNum): v is number =>
  typeof v === "number" && Number.isFinite(v);

export const fmtNum = (v: MaybeNum, digits = 2) =>
  isNum(v) ? v.toFixed(digits) : "—";
export const fmtPctOpt = (v: MaybeNum, digits = 0) =>
  isNum(v) ? `${(v * 100).toFixed(digits)}%` : "—";
export const fmtMmOpt = (v: MaybeNum) => (isNum(v) ? `${v.toFixed(0)} mm` : "—");

/** Explicit UI states for nullable model outputs (AVAILABLE/UNAVAILABLE/...). */
export type NullState = "AVAILABLE" | "UNAVAILABLE" | "PROCESSING" | "ERROR";
export const nullState = (v: MaybeNum): "AVAILABLE" | "UNAVAILABLE" =>
  isNum(v) ? "AVAILABLE" : "UNAVAILABLE";

export const fmtTime = (iso: string) =>
  new Date(iso).toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });

export const fmtCoord = (v: number, digits = 4) => v.toFixed(digits);

export const relativeAge = (iso: string): string => {
  const hrs = (Date.now() - new Date(iso).getTime()) / 3.6e6;
  if (hrs < 1) return "just now";
  if (hrs < 24) return `${Math.round(hrs)}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
};

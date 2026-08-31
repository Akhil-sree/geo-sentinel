export const fmtPct = (v: number, digits = 0) => `${(v * 100).toFixed(digits)}%`;

export const fmtMm = (v: number) => `${v.toFixed(0)} mm`;

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

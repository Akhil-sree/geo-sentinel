import { api } from "./client";

/** gs_v1 point assessment — mirrors the backend contract exactly:
 *  risk_score/temporal_risk are nullable (null = data unavailable, not zero).
 *  temporal_risk is always null: the temporal model is chance-level and
 *  deliberately unwired from operational risk. */
export interface GsPointResult {
  risk_score: number | null;
  risk_level: string;
  susceptibility: number | null;
  temporal_risk: null;
  landslide_detected: boolean;
  confidence: number;
  note?: string;
  error?: string;
}

export type GsState = "AVAILABLE" | "UNAVAILABLE" | "PROCESSING" | "ERROR";

/** Classify a gs response into an explicit UI state (never coerce null→0). */
export function gsDisplayState(
  loading: boolean,
  error: string | null,
  result: GsPointResult | null,
): GsState {
  if (loading) return "PROCESSING";
  if (error) return "ERROR";
  if (
    !result ||
    typeof result.risk_score !== "number" ||
    !Number.isFinite(result.risk_score)
  )
    return "UNAVAILABLE";
  return "AVAILABLE";
}

export const getGsPoint = (lat: number, lon: number) =>
  api
    .get<GsPointResult>("/risk/gs_point", { params: { lat, lon } })
    .then((r) => r.data);

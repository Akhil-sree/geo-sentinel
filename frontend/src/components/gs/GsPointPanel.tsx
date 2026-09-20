import { useEffect, useState } from "react";
import { getGsPoint, gsDisplayState, type GsPointResult } from "../../api/gs";
import { fmtNum } from "../../lib/format";

/** Live gs_v1 assessment for the selected map location.
 *  Uses the real GET /api/risk/gs_point endpoint — no mocks, no simulated
 *  values. Temporal prediction is displayed as UNAVAILABLE because the
 *  backend returns temporal_risk: null (Mamba chance-level, unwired). */
export default function GsPointPanel({
  lat,
  lng,
  label,
}: {
  lat: number;
  lng: number;
  label: string;
}) {
  const [result, setResult] = useState<GsPointResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setResult(null);
    getGsPoint(lat, lng)
      .then((r) => {
        if (r && typeof r === "object" && "error" in r && !("risk_level" in r)) {
          setError(String((r as unknown as { error: unknown }).error));
        } else {
          setResult(r);
        }
      })
      .catch((e) =>
        setError(
          e?.response?.status === 422
            ? "Invalid coordinates for model assessment."
            : "Model service unreachable — is the backend running?",
        ),
      )
      .finally(() => setLoading(false));
  }, [lat, lng]);

  const state = gsDisplayState(loading, error, result);

  return (
    <div
      className="rounded-lg p-4"
      style={{
        background: "#FFFFFF",
        border: "1px solid #E5E7EB",
      }}
      data-testid="gs-point-panel"
      data-state={state}
    >
      <p className="text-[11px] font-semibold uppercase tracking-wider text-gs-text-secondary">
        Model assessment · {label}
      </p>
      {state === "PROCESSING" && (
        <p className="mt-2 text-[14px] text-gs-text-secondary">Assessing…</p>
      )}
      {state === "ERROR" && (
        <p className="mt-2 text-[14px] font-medium text-risk-critical">{error}</p>
      )}
      {state === "UNAVAILABLE" && (
        <div className="mt-2">
          <p className="text-[14px] font-medium text-gs-text">
            Risk score: unavailable for this location
          </p>
          <p className="mt-1 text-[12px] text-gs-text-secondary">
            Outside model coverage — no value is estimated rather than filling
            a silent default.
          </p>
        </div>
      )}
      {state === "AVAILABLE" && result && (
        <div className="mt-2">
          <div className="flex items-baseline justify-between">
            <span className="text-[14px] text-gs-text-secondary">
              Current risk · {result.risk_level}
            </span>
            <span className="text-[28px] font-bold text-gs-text">
              {fmtNum(result.risk_score)}
            </span>
          </div>
          <p className="mt-1 text-[12px] text-gs-text-secondary">
            Risk score (uncalibrated model output, 0–1 — not a probability).
          </p>
          <div className="mt-2 border-t border-gs-border/60 pt-2">
            <p className="text-[14px] font-medium text-gs-text">
              Temporal prediction: unavailable
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

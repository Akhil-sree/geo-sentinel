import { useEffect, useState, useRef } from "react";
import {
  analyzeVisionImage,
  getVisionObservations,
  getVisionModelStatus,
  getVisionCorroboration,
} from "../../api/dashboard";
import { useUIStore } from "../../store/uiStore";
import { fmtPctOpt } from "../../lib/format";
import Spinner from "../common/Spinner";
import type { VisionObservationRecord, VisionModelStatus, CorroborationResult } from "../../types/risk";

const SEVERITY_COLORS: Record<string, string> = {
  HIGH: "#ba1a1a",
  MODERATE: "#ea580c",
  LOW: "#d97706",
  NONE: "#2563EB",
};

const CORROBORATION_COLORS: Record<string, string> = {
  CORROBORATED: "#2563EB",
  VISUAL_ANOMALY: "#ba1a1a",
  INCONCLUSIVE: "#d97706",
  LOW_CONCERN: "#2563EB",
  NO_ZONE_DATA: "#999",
  NO_OBSERVATIONS: "#999",
};

export default function ObservationIntelligencePanel() {
  const selectedZoneId = useUIStore((s) => s.selectedZoneId);
  const fileRef = useRef<HTMLInputElement>(null);

  const [modelStatus, setModelStatus] = useState<VisionModelStatus | null>(null);
  const [observations, setObservations] = useState<VisionObservationRecord[]>([]);
  const [corroboration, setCorroboration] = useState<CorroborationResult | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [lastResult, setLastResult] = useState<any>(null);

  useEffect(() => {
    getVisionModelStatus().then(setModelStatus).catch(() => {});
    getVisionObservations(20).then((d) => setObservations(d.observations || [])).catch(() => {});
  }, []);

  useEffect(() => {
    if (selectedZoneId) {
      getVisionCorroboration(selectedZoneId).then(setCorroboration).catch(() => setCorroboration(null));
    }
  }, [selectedZoneId]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setAnalyzing(true);
    setLastResult(null);
    try {
      const result = await analyzeVisionImage(
        file,
        undefined,
        undefined,
        undefined,
        selectedZoneId || undefined,
      );
      setLastResult(result);
      // Refresh observations list
      getVisionObservations(20).then((d) => setObservations(d.observations || [])).catch(() => {});
      if (selectedZoneId) {
        getVisionCorroboration(selectedZoneId).then(setCorroboration).catch(() => {});
      }
    } catch {
      setLastResult({ warning: "Analysis failed — backend may be unreachable" });
    } finally {
      setAnalyzing(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <div className="rounded-card p-4" style={{
      background: "rgba(229, 233, 224, 0.45)",
      backdropFilter: "blur(8px)",
      border: "1px solid rgba(255,255,255,0.18)",
    }}>
      <h3 className="text-[15px] font-bold text-gs-text mb-1">Observation Intelligence</h3>
      <p className="text-[12px] text-gs-text-secondary mb-3">
        SegFormer semantic segmentation for visual landslide evidence
      </p>

      {/* Model Status */}
      {modelStatus && (
        <div className="flex flex-wrap gap-2 mb-3">
          <span className="px-2 py-1 rounded-full text-[10px] font-bold text-white" style={{
            background: modelStatus.status === "LOADED" ? "#2563EB" : "#d97706",
          }}>
            {modelStatus.model.toUpperCase()} — {modelStatus.status}
          </span>
          {!modelStatus.trained_landslide && (
            <span className="px-2 py-1 rounded-full text-[10px] font-medium text-orange-800" style={{ background: "rgba(234,88,12,0.15)" }}>
              Not a trained landslide detector
            </span>
          )}
        </div>
      )}

      {/* Upload */}
      <div className="mb-3">
        <input
          ref={fileRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={handleUpload}
          className="hidden"
          id="vision-upload"
        />
        <label
          htmlFor="vision-upload"
          className="flex items-center justify-center gap-2 w-full rounded-card border-2 border-dashed border-forest/30 bg-white/30 py-4 text-[13px] font-semibold text-forest cursor-pointer transition hover:bg-white/50 hover:border-forest/50"
        >
          {analyzing ? (
            <><Spinner /> Analyzing image...</>
          ) : (
            <> Upload field/satellite image for analysis</>
          )}
        </label>
      </div>

      {/* Last analysis result */}
      {lastResult && (
        <div className="mb-3 space-y-2">
          <div className="rounded-lg p-3" style={{
            background: lastResult.landslide_detected ? "rgba(186,26,26,0.08)" : "rgba(36,92,69,0.08)",
            borderLeft: `3px solid ${SEVERITY_COLORS[lastResult.observation_severity] || "#999"}`,
          }}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[13px] font-bold text-gs-text">
                {lastResult.landslide_detected ? "Visual landslide-like region detected" : "No significant landslide region detected"}
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold text-white"
                style={{ background: SEVERITY_COLORS[lastResult.observation_severity] || "#999" }}>
                {lastResult.observation_severity}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2 text-[11px]">
              <div>
                <span className="text-gs-text-secondary">Confidence</span>
                <div className="font-bold text-gs-text">{fmtPctOpt(lastResult.confidence, 1)}</div>
              </div>
              <div>
                <span className="text-gs-text-secondary">Affected Area</span>
                <div className="font-bold text-gs-text">{fmtPctOpt(lastResult.affected_pixel_ratio, 1)}</div>
              </div>
              <div>
                <span className="text-gs-text-secondary">Regions</span>
                <div className="font-bold text-gs-text">{lastResult.num_regions || 0}</div>
              </div>
            </div>
            {lastResult.warning && (
              <div className="mt-2 text-[10px] text-orange-700 bg-orange-50/60 rounded px-2 py-1">{lastResult.warning}</div>
            )}
          </div>

          {/* Corroboration */}
          {lastResult.corroboration && (
            <div className="rounded-lg p-2.5" style={{
              background: "rgba(255,255,255,0.4)",
              borderLeft: `3px solid ${CORROBORATION_COLORS[lastResult.corroboration.corroboration] || "#999"}`,
            }}>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[11px] font-bold text-gs-text">Risk Corroboration:</span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold text-white"
                  style={{ background: CORROBORATION_COLORS[lastResult.corroboration.corroboration] || "#999" }}>
                  {lastResult.corroboration.corroboration}
                </span>
              </div>
              <p className="text-[11px] text-gs-text-secondary">{lastResult.corroboration.explanation}</p>
            </div>
          )}
        </div>
      )}

      {/* Zone corroboration (when zone selected) */}
      {corroboration && !lastResult && (
        <div className="mb-3 rounded-lg p-2.5" style={{
          background: "rgba(255,255,255,0.4)",
          borderLeft: `3px solid ${CORROBORATION_COLORS[corroboration.corroboration] || "#999"}`,
        }}>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[11px] font-bold text-gs-text">Zone Corroboration:</span>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold text-white"
              style={{ background: CORROBORATION_COLORS[corroboration.corroboration] || "#999" }}>
              {corroboration.corroboration}
            </span>
          </div>
          <p className="text-[11px] text-gs-text-secondary">{corroboration.explanation}</p>
        </div>
      )}

      {/* Recent observations */}
      {observations.length > 0 && (
        <div>
          <div className="text-[11px] font-semibold text-gs-text-secondary uppercase tracking-wide mb-2">
            Recent Observations ({observations.length})
          </div>
          <div className="space-y-1.5 max-h-48 overflow-y-auto">
            {observations.slice(0, 8).map((obs) => (
              <div key={obs.id} className="flex items-center justify-between rounded-lg px-3 py-2" style={{
                background: "rgba(255,255,255,0.35)",
                borderLeft: `3px solid ${SEVERITY_COLORS[obs.severity] || "#999"}`,
              }}>
                <div className="flex-1">
                  <div className="text-[12px] font-semibold text-gs-text">
                    {obs.zone_id || "Unknown zone"} — {fmtPctOpt(obs.confidence)} confidence
                  </div>
                  <div className="text-[10px] text-gs-text-secondary">
                    {obs.model_name} · {fmtPctOpt(obs.pixel_ratio, 1)} affected
                    {obs.created_at && ` · ${new Date(obs.created_at).toLocaleString()}`}
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded-full text-[9px] font-bold text-white"
                  style={{ background: SEVERITY_COLORS[obs.severity] || "#999" }}>
                  {obs.severity}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

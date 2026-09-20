import { useEffect, useState } from "react";
import { getZoneEvidence } from "../../api/risk";
import { useUIStore } from "../../store/uiStore";
import { fmtPctOpt, fmtMmOpt } from "../../lib/format";
import Spinner from "../common/Spinner";
import type { ZoneEvidence } from "../../types/risk";

const STATE_COLORS: Record<string, string> = {
  CRITICAL: "#B91C1C",
  DEGRADING: "#EA580C",
  STRESSED: "#D97706",
  STABLE: "#2563EB",
};

export default function WhyThisLocation() {
  const [evidence, setEvidence] = useState<ZoneEvidence | null>(null);
  const [loading, setLoading] = useState(false);
  const simTime = useUIStore((s) => s.simTime);
  const selectedZoneId = useUIStore((s) => s.selectedZoneId);

  useEffect(() => {
    if (!selectedZoneId) { setEvidence(null); return; }
    setLoading(true);
    getZoneEvidence(selectedZoneId, simTime)
      .then(setEvidence)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [selectedZoneId, simTime]);

  if (!selectedZoneId) return null;
  if (loading) return (
    <div className="p-3 flex items-center gap-2 text-[13px] text-gs-text-secondary">
      <Spinner /> Loading model inputs…
    </div>
  );
  if (!evidence) return null;

  const t = evidence.terrain;
  const rf = evidence.rainfall;
  const st = evidence.slope_state;
  const sm = evidence.soil_moisture;
  const dem = t?.dem_observed;

  return (
    <div>
      <div className="gs-label mb-3">Model Input Summary</div>

      {/* Terrain inputs */}
      {t && (
        <div className="mb-3">
          <div className="gs-label mb-1.5" style={{ fontSize: 9, color: '#5F6B62' }}>TERRAIN</div>
          <div className="grid grid-cols-2 gap-1.5">
            <InputChip label="Slope" value={t.slope != null ? `${t.slope}°` : "—"} />
            <InputChip label="Elevation" value={t.elevation != null ? `${t.elevation}m` : "—"} />
            <InputChip label="Ruggedness" value={t.ruggedness != null ? t.ruggedness.toFixed(2) : "—"} />
            <InputChip label="Population" value={t.population != null ? String(t.population) : "—"} />
          </div>
          {dem && (
            <div className="mt-1.5 grid grid-cols-3 gap-1.5">
              <InputChip label="Aspect" value={`${dem.aspect_deg}°`} small />
              <InputChip label="Relief" value={`${dem.relief_m}m`} small />
              <InputChip label="DEM" value={dem.source} small />
            </div>
          )}
        </div>
      )}

      {/* Rainfall inputs */}
      <div className="mb-3">
        <div className="gs-label mb-1.5" style={{ fontSize: 9, color: '#5F6B62' }}>RAINFALL</div>
        <div className="grid grid-cols-3 gap-1.5">
          <InputChip label="24h" value={fmtMmOpt(rf["24h"])} />
          <InputChip label="72h" value={fmtMmOpt(rf["72h"])} />
          <InputChip label="7d" value={fmtMmOpt(rf["7d"])} />
        </div>
        <div className="mt-1.5 grid grid-cols-2 gap-1.5">
          <InputChip label="Trend" value={rf.slope > 0 ? `+${rf.slope.toFixed(2)}` : rf.slope.toFixed(2)} />
          <InputChip label="Soil moisture" value={sm != null ? `${(sm * 100).toFixed(0)}%` : "—"} />
        </div>
      </div>

      {/* Model components */}
      <div className="mb-3">
        <div className="gs-label mb-1.5" style={{ fontSize: 9, color: '#5F6B62' }}>MODEL COMPONENTS</div>
        <div className="space-y-1">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-gs-text-secondary">Static susceptibility (RF)</span>
            <span className="font-semibold text-gs-text">{fmtPctOpt(evidence.static_score)}</span>
          </div>
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-gs-text-secondary">Dynamic risk (Mamba)</span>
            <span className="font-semibold text-gs-text">{fmtPctOpt(evidence.dynamic_score)}</span>
          </div>
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-gs-text-secondary">Slope stress index</span>
            <span className="font-semibold" style={{ color: st.color }}>{fmtPctOpt(st.stress_score)}</span>
          </div>
        </div>
      </div>

      {/* Slope state */}
      <div className="mb-3">
        <div className="gs-label mb-1.5" style={{ fontSize: 9, color: '#5F6B62' }}>SLOPE STATE</div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-bold text-white"
            style={{ background: STATE_COLORS[st.state] || "#65736C" }}>
            {st.state}
          </span>
          <span className="text-[11px] text-gs-text-secondary">{st.label}</span>
        </div>
      </div>

      {/* Key drivers */}
      {evidence.drivers.length > 0 && (
        <div className="mb-3">
          <div className="gs-label mb-1.5" style={{ fontSize: 9, color: '#5F6B62' }}>KEY DRIVERS</div>
          <div className="space-y-1">
            {evidence.drivers.slice(0, 5).map((d, i) => (
              <div key={i} className="flex items-center gap-2 text-[11px]">
                <span className="text-gs-text-secondary flex-1">{d.factor}</span>
                <span className="font-semibold text-gs-text">{(d.impact * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Landslide history */}
      {evidence.history && evidence.history.length > 0 && (
        <div className="mb-3">
          <div className="gs-label mb-1.5" style={{ fontSize: 9, color: '#5F6B62' }}>LANDSLIDE HISTORY</div>
          <div className="space-y-1">
            {evidence.history.slice(0, 3).map((h, i) => (
              <div key={i} className="flex items-center gap-2 text-[11px]">
                <span className="text-gs-text-secondary">{h.event_date ?? "Unknown date"}</span>
                <span className="font-medium text-gs-text">{h.type}</span>
                <span className="text-gs-text-secondary">({h.source})</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Data freshness */}
      {evidence.freshness && (
        <div className="mb-3">
          <div className="gs-label mb-1.5" style={{ fontSize: 9, color: '#5F6B62' }}>DATA FRESHNESS</div>
          <div className="space-y-1">
            {evidence.freshness.rainfall && (
              <div className="flex items-center gap-2 text-[11px]">
                <span className="text-gs-text-secondary">Rainfall:</span>
                <span className="text-gs-text">{evidence.freshness.rainfall.source ?? "—"}</span>
                {evidence.freshness.rainfall.observed_at && (
                  <span className="text-gs-text-secondary">({evidence.freshness.rainfall.observed_at})</span>
                )}
              </div>
            )}
            {evidence.freshness.soil_moisture && (
              <div className="flex items-center gap-2 text-[11px]">
                <span className="text-gs-text-secondary">Soil moisture:</span>
                <span className="text-gs-text">{evidence.freshness.soil_moisture.source ?? "—"}</span>
                {evidence.freshness.soil_moisture.observed_at && (
                  <span className="text-gs-text-secondary">({evidence.freshness.soil_moisture.observed_at})</span>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Model versions */}
      <div className="pt-2 border-t border-gs-border/60">
        <div className="flex items-center gap-3 text-[9px] text-gs-text-secondary">
          <span>RF: {evidence.model_versions.rf}</span>
          <span>Mamba: {evidence.model_versions.mamba}</span>
          <span>Fusion: {evidence.model_versions.fusion}</span>
        </div>
      </div>
    </div>
  );
}

function InputChip({ label, value, small }: { label: string; value: string; small?: boolean }) {
  return (
    <div className={`rounded-md px-2 py-1 ${small ? "" : ""}`} style={{ background: '#F4F1EB' }}>
      <div className="text-[9px] font-bold uppercase tracking-wide text-gs-text-secondary">{label}</div>
      <div className={`${small ? "text-[10px]" : "text-[12px]"} font-semibold text-gs-text`}>{value}</div>
    </div>
  );
}

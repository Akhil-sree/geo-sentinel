import { useEffect, useState } from "react";
import { getDataFreshness } from "../../api/admin";
import { getDataStatus, type ProviderState } from "../../api/risk";

interface Chip {
  name: string;
  status: string;
  color: string;
  title?: string;
}

const FALLBACK: Chip[] = [
  { name: "Rainfall (SIMULATED)", status: "Simulated", color: "#E55A2B" },
  { name: "Soil moisture (SIMULATED)", status: "Simulated", color: "#E55A2B" },
  { name: "Satellite SAR", status: "Excluded from risk", color: "#B91C1C" },
  { name: "Terrain (STATIC)", status: "Static baseline", color: "#6B7280" },
];

const PRETTY: Record<string, string> = {
  rainfall: "Rainfall",
  soil_moisture: "Soil moisture",
  sentinel1_sar: "Satellite SAR",
};

function ageLabel(iso: string | null): string {
  if (!iso) return "";
  const mins = Math.max(0, (Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${Math.round(mins)} min ago`;
  return `${Math.round(mins / 60)} h ago`;
}

export function chipFor(p: ProviderState): Chip {
  const name = PRETTY[p.source] ?? p.source;
  const cleanTitle = p.quality ? p.quality.replace(/SATELLITE_DEMO|DEMO_DATA/gi, "Standby data").replace(/DEMO/gi, "Standby").trim() : undefined;
  if (p.is_live) {
    return {
      name: `${name} (LIVE)`,
      status: `Live · updated ${ageLabel(p.observed_at)}`,
      color: "#1FAF6B",
      title: cleanTitle,
    };
  }
  if (/STALE/i.test(p.freshness)) {
    return { name: `${name} (STALE)`, status: "Stale — last good data kept", color: "#E55A2B", title: cleanTitle };
  }
  if (p.source === "sentinel1_sar") {
    return { name, status: "Excluded from risk", color: "#B91C1C", title: cleanTitle };
  }
  const extra = p.soil_moisture_source ? ` · ${p.soil_moisture_source}` : "";
  return { name: `${name} (SIMULATED${extra})`, status: "Simulated", color: "#E55A2B", title: cleanTitle };
}

export default function DataFreshnessBar() {
  const [chips, setChips] = useState<Chip[]>(FALLBACK);
  const [mode, setMode] = useState<string>("");

  useEffect(() => {
    // Honest endpoint first (is_live flags); legacy admin feed as fallback.
    getDataStatus()
      .then((d) => {
        setChips(d.providers.map(chipFor));
        setMode(d.mode);
      })
      .catch(() =>
        getDataFreshness()
          .then((data) =>
            setChips(
              (data?.freshness ?? []).map((f: any) => ({
                name: SOURCE_LABELS[f.source] ?? f.source,
                status: getStateLabel(f.state),
                color: getStateColorHex(f.state),
              }))
            )
          )
          .catch(() => {})
      );
  }, []);

  // Compact status semantics derived from the honest chip data.
  const rowState = (s: Chip): { dot: string; label: string; filled: boolean; note?: string } => {
    const n = s.name.toUpperCase();
    if (n.includes("LIVE")) return { dot: "#1FAF6B", label: "LIVE", filled: true };
    if (n.includes("STALE")) return { dot: "#E55A2B", label: "STALE", filled: true };
    if (n.includes("SAR") || n.includes("STANDBY"))
      return { dot: "#9AA3A0", label: "NOT USED", filled: false, note: "excluded from risk" };
    if (n.includes("MODEL")) return { dot: "#5B6B7A", label: "MODELED", filled: true };
    if (n.includes("STATIC")) return { dot: "#9AA3A0", label: "STATIC", filled: true };
    return { dot: "#D19217", label: "SIMULATED", filled: true };
  };
  const shortName = (s: Chip) =>
    s.name.replace(/\s*\((LIVE|STALE|DEMO|SIMULATED[^)]*|STATIC[^)]*)\)\s*/gi, "").replace(/DEMO/gi, "").trim();

  return (
    <div className="px-4 py-2" style={{
      background: '#FAFAF8',
      borderBottom: '1px solid #E5E7EB',
    }}>
      <div className="mb-1 flex items-center gap-2">
        <span className="gs-label" style={{ color: '#075240' }}>
          Data Sources
        </span>
        {mode && !/demo/i.test(mode) && (
          <span className="rounded px-1 py-px text-[8px] font-bold uppercase tracking-wider" style={{
            background: 'rgba(7,82,64,0.08)',
            color: '#075240',
          }}>
            {mode}
          </span>
        )}
      </div>

      <ul className="space-y-0.5" role="status" aria-label="Data source status">
        {chips.map((s) => {
          const st = rowState(s);
          return (
            <li key={s.name} title={s.title || s.status} className="flex items-center gap-2 text-[11px]">
              <span
                aria-hidden
                className="inline-block h-1.5 w-1.5 shrink-0 rounded-full"
                style={{
                  background: st.filled ? st.dot : "transparent",
                  border: `1.5px solid ${st.dot}`,
                }}
              />
              <span className="min-w-0 flex-1 truncate font-medium text-gs-text">{shortName(s)}</span>
              <span className="shrink-0 text-[9px] font-bold uppercase tracking-wider" style={{ color: st.dot }}>
                {st.label}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

const SOURCE_LABELS: Record<string, string> = {
  RAINFALL: "IMD Rainfall",
  SOIL: "SMAP Soil Moisture",
  SAR: "Sentinel-1 SAR",
  ELEVATION: "Elevation",
  TERRAIN: "Terrain",
};

function getStateLabel(state: string): string {
  if (/demo|standby/i.test(state)) return "Standby";
  if (state.includes("6d old")) return "6d old";
  if (state.includes("VERY_STALE") || state.includes("VERY OLD")) return "Very Stale";
  if (state.includes("2d old") || state.includes("3d old")) return "2d old";
  if (state.includes("STALE")) return "Stale";
  if (state.includes("FRESH")) return "Fresh";
  if (state.includes("LIVE")) return "Live";
  return state;
}

function getStateColorHex(state: string): string {
  if (state.includes("VERY_STALE") || state.includes("VERY OLD") || state.includes("6d old"))
    return "#B91C1C";
  if (state.includes("STALE") || state.includes("2d old") || state.includes("3d old"))
    return "#E55A2B";
  if (/demo|standby/i.test(state))
    return "#1FAF6B";
  if (state.includes("FRESH") || state.includes("LIVE"))
    return "#1FAF6B";
  return "#1FAF6B";
}

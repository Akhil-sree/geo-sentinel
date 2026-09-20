import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getAlerts } from "../api/alerts";
import { useI18n } from "../lib/i18n";

const SEV_CONFIG: Record<string, { color: string; bg: string; label: string; icon: string }> = {
  VERY_HIGH: { color: "#B4232B", bg: "#B4232B10", label: "CRITICAL RISK", icon: "⚠" },
  CRITICAL:  { color: "#B4232B", bg: "#B4232B10", label: "CRITICAL RISK", icon: "⚠" },
  HIGH:      { color: "#E76016", bg: "#E7601610", label: "HIGH RISK", icon: "⚠" },
  MODERATE:  { color: "#D19217", bg: "#D1921710", label: "MODERATE RISK", icon: "⚠" },
  LOW:       { color: "#2563EB", bg: "#2563EB10", label: "LOW RISK", icon: "⚠" },
};

function getSeverityConfig(severity: string) {
  return SEV_CONFIG[severity?.toUpperCase()] ?? SEV_CONFIG.LOW;
}

function WarningIcon({ color, size = 32 }: { color: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <path
        d="M16 3L2 29h28L16 3z"
        fill={color}
        opacity="0.15"
        stroke={color}
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <line x1="16" y1="13" x2="16" y2="21" stroke={color} strokeWidth="2.5" strokeLinecap="round" />
      <circle cx="16" cy="25" r="1.5" fill={color} />
    </svg>
  );
}

function formatTime(at: string): string {
  if (!at) return "";
  try {
    const d = new Date(at);
    return d.toLocaleString("en-IN", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
      timeZone: "Asia/Kolkata",
    }) + " IST";
  } catch {
    return at;
  }
}

export default function AlertConsole() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const navigate = useNavigate();
  const { t } = useI18n();

  useEffect(() => { getAlerts().then(setAlerts).catch(() => {}); }, []);

  return (
    <main className="overflow-y-auto bg-gs-bg p-6">
      <div className="mx-auto max-w-4xl space-y-6">

        {/* Page Header */}
        <div>
          <h1 className="text-[24px] font-bold text-gs-text tracking-tight">
            {t("alerts.title")}
          </h1>
          <p className="mt-1 text-[14px] text-gs-text-secondary">
            {t("alerts.subtitle")}
          </p>
        </div>

        {/* Alert Cards */}
        <div className="space-y-3">
          {alerts.map((a, i) => {
            const cfg = getSeverityConfig(a.severity);
            return (
              <div
                key={i}
                className="rounded-xl border-l-4 overflow-hidden transition"
                style={{
                  background: 'rgba(255, 255, 255, 0.52)',
                  backdropFilter: 'blur(8px)',
                  WebkitBackdropFilter: 'blur(8px)',
                  border: '1px solid rgba(214, 208, 196, 0.35)',
                  borderLeftColor: cfg.color,
                  boxShadow: '0 2px 12px rgba(42, 51, 45, 0.05)',
                }}
              >
                <div className="flex items-center gap-4 p-5">

                  {/* Warning Icon */}
                  <div className="shrink-0">
                    <WarningIcon color={cfg.color} size={36} />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    {/* Title */}
                    <h3 className="text-[18px] font-bold text-gs-text leading-tight">
                      <span style={{ color: cfg.color }}>{cfg.label}</span>
                      <span className="text-gs-text-secondary font-normal"> — </span>
                      <span className="text-gs-text">{a.zone_id}</span>
                    </h3>

                    {/* Supporting info */}
                    <p className="text-[14px] text-gs-text-secondary mt-1.5 leading-relaxed">
                      {formatTime(a.at) && <span>Updated {formatTime(a.at)}</span>}
                      {a.message && <span> · {a.message}</span>}
                      {!a.message && !formatTime(a.at) && <span>Zone advisory dispatched</span>}
                    </p>

                    {/* Metadata row */}
                    <div className="flex items-center gap-3 mt-2 text-[12px] text-gs-text-muted">
                      {a.to && <span>📱 {a.to}</span>}
                      {a.lang && <span>🌐 {a.lang?.toUpperCase()}</span>}
                      {a.status && (
                        <span className="ml-auto text-[12px] font-semibold" style={{ color: cfg.color }}>
                          {a.status}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Action Button */}
                  <div className="shrink-0">
                    <button
                      onClick={() => navigate("/")}
                      className="rounded-lg border-2 px-5 py-2.5 text-[14px] font-semibold transition-colors"
                      style={{
                        borderColor: cfg.color,
                        color: cfg.color,
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = cfg.color;
                        e.currentTarget.style.color = "#fff";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = "transparent";
                        e.currentTarget.style.color = cfg.color;
                      }}
                    >
                      View on map
                    </button>
                  </div>
                </div>
              </div>
            );
          })}

          {alerts.length === 0 && (
            <div className="rounded-xl p-10 text-center" style={{
              background: 'rgba(255, 255, 255, 0.48)',
              backdropFilter: 'blur(6px)',
              WebkitBackdropFilter: 'blur(6px)',
              border: '1px solid rgba(214, 208, 196, 0.30)',
              boxShadow: '0 1px 8px rgba(42, 51, 45, 0.04)',
            }}>
              <div className="mb-3">
                <WarningIcon color="#D4CFC4" size={40} />
              </div>
              <p className="text-[16px] font-medium text-gs-text-secondary">
                {t("alerts.noAlerts")}
              </p>
              <p className="text-[14px] text-gs-text-secondary/70 mt-1">
                {t("alerts.emptyHint")}
              </p>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

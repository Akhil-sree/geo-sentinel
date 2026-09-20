import type { SlopeState } from "../../types/risk";

const STATE_STYLES: Record<SlopeState, { bg: string; text: string; icon: string; ring: string }> = {
  STABLE: { bg: "bg-risk-stable", text: "text-white", icon: "✓", ring: "ring-risk-stable/20" },
  STRESSED: { bg: "bg-risk-stressed", text: "text-white", icon: "▲", ring: "ring-risk-stressed/20" },
  DEGRADING: { bg: "bg-risk-degrading", text: "text-white", icon: "▲▲", ring: "ring-risk-degrading/20" },
  CRITICAL: { bg: "bg-risk-critical", text: "text-white", icon: "⚠", ring: "ring-risk-critical/20" },
};

const STATE_LABELS: Record<SlopeState, string> = {
  STABLE: "Stable",
  STRESSED: "Stressed",
  DEGRADING: "Degrading",
  CRITICAL: "Critical",
};

interface SlopeStateBadgeProps {
  state: SlopeState;
  label?: string;
  size?: "sm" | "md" | "lg";
  showIcon?: boolean;
  stressScore?: number;
}

export default function SlopeStateBadge({
  state,
  label,
  size = "md",
  showIcon = true,
  stressScore,
}: SlopeStateBadgeProps) {
  const style = STATE_STYLES[state];
  const sizeClasses = {
    sm: "px-2 py-0.5 text-[10px]",
    md: "px-2.5 py-1 text-[12px]",
    lg: "px-3 py-1.5 text-[13px]",
  };

  return (
    <div className="inline-flex flex-col gap-1">
      <span
        className={`inline-flex items-center gap-1.5 rounded-full font-medium ring-1 ${style.bg} ${style.text} ${style.ring} ${sizeClasses[size]}`}
      >
        {showIcon && <span className="text-[10px]">{style.icon}</span>}
        {label ?? STATE_LABELS[state]}
      </span>
      {stressScore != null && (
        <div className="flex items-center gap-1.5 px-1">
          <div className="h-1.5 flex-1 rounded-full bg-gs-border">
            <div className="h-1.5 rounded-full transition-all duration-500" style={{
              width: `${Math.min(100, stressScore * 100)}%`,
              backgroundColor: style.bg.replace("bg-[", "").replace("]", ""),
            }} />
          </div>
          <span className="text-[11px] text-gs-text-secondary">{(stressScore * 100).toFixed(0)}%</span>
        </div>
      )}
    </div>
  );
}

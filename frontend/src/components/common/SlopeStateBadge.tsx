import type { SlopeState } from "../../types/risk";

const STATE_STYLES: Record<SlopeState, { bg: string; text: string; icon: string; ring: string }> = {
  STABLE: { bg: "bg-[#245c45]", text: "text-white", icon: "\u2713", ring: "ring-[#245c45]/30" },
  STRESSED: { bg: "bg-[#d97706]", text: "text-white", icon: "\u25B2", ring: "ring-[#d97706]/30" },
  DEGRADING: { bg: "bg-[#ea580c]", text: "text-white", icon: "\u25B2\u25B2", ring: "ring-[#ea580c]/30" },
  CRITICAL: { bg: "bg-[#ba1a1a]", text: "text-white", icon: "\u26A0", ring: "ring-[#ba1a1a]/30" },
};

const STATE_LABELS: Record<SlopeState, string> = {
  STABLE: "STABLE",
  STRESSED: "STRESSED",
  DEGRADING: "DEGRADING",
  CRITICAL: "CRITICAL",
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
    sm: "px-1.5 py-0.5 text-[8px]",
    md: "px-2 py-0.5 text-[10px]",
    lg: "px-3 py-1 text-xs",
  };

  return (
    <div className="inline-flex flex-col gap-0.5">
      <span
        className={`inline-flex items-center gap-1 rounded-full font-bold ring-1 ${style.bg} ${style.text} ${style.ring} ${sizeClasses[size]}`}
      >
        {showIcon && <span className="text-[8px]">{style.icon}</span>}
        {label ?? STATE_LABELS[state]}
      </span>
      {stressScore != null && (
        <div className="flex items-center gap-1 px-1">
          <div className="h-1 flex-1 rounded-full bg-gray-200">
            <div className="h-1 rounded-full transition-all duration-500" style={{
              width: `${Math.min(100, stressScore * 100)}%`,
              backgroundColor: style.bg.replace("bg-[", "").replace("]", ""),
            }} />
          </div>
          <span className="text-[7px] text-gray-500">{(stressScore * 100).toFixed(0)}%</span>
        </div>
      )}
    </div>
  );
}

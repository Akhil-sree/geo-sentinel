import type { Driver } from "../../types/risk";

export default function DriverBars({ drivers }: { drivers: Driver[] }) {
  const max = Math.max(...drivers.map((d) => d.impact), 0.001);
  return (
    <div className="space-y-2">
      {drivers.map((d) => (
        <div key={d.factor} className="flex items-center gap-2 text-[10px]">
          <span className="w-52 shrink-0 text-gs-text-secondary">{d.factor}</span>
          <div className="h-1.5 flex-1 rounded-full bg-gs-border">
            <div className="h-1.5 rounded-full bg-gradient-to-r from-forest to-risk-degrading"
                 style={{ width: `${(d.impact / max) * 100}%` }} />
          </div>
          <span className="w-16 text-right font-medium text-gs-text-secondary">
            {d.impact > 0.6 ? "High" : d.impact > 0.3 ? "Moderate" : "Low"}
          </span>
        </div>
      ))}
    </div>
  );
}

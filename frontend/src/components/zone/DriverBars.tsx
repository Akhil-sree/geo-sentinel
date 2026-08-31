import type { Driver } from "../../types/risk";

export default function DriverBars({ drivers }: { drivers: Driver[] }) {
  const max = Math.max(...drivers.map((d) => d.impact), 0.001);
  return (
    <div className="space-y-2">
      {drivers.map((d) => (
        <div key={d.factor} className="flex items-center gap-2 text-xs">
          <span className="w-52 shrink-0 text-slate-400">{d.factor}</span>
          <div className="h-2 flex-1 rounded bg-slate-800">
            <div className="h-2 rounded bg-gradient-to-r from-sky-600 to-orange-500"
                 style={{ width: `${(d.impact / max) * 100}%` }} />
          </div>
          <span className="w-16 text-right font-mono text-slate-500">
            {d.impact > 0.6 ? "HIGH" : d.impact > 0.3 ? "MODERATE" : "LOW"}
          </span>
        </div>
      ))}
    </div>
  );
}

import type { CitizenReport } from "../../types/report";

const STATUS_CLS: Record<string, string> = {
  PENDING: "bg-amber-950 text-amber-400",
  VERIFIED: "bg-emerald-950 text-emerald-400",
  REJECTED: "bg-red-950 text-red-400",
  USED_FOR_TRAINING: "bg-sky-950 text-sky-400",
};

export default function ReportList({ reports }: { reports: CitizenReport[] }) {
  return (
    <ul className="space-y-2">
      {reports.map((r) => (
        <li key={r.id} className="rounded border border-slate-800 bg-slate-900/60 p-2 text-xs">
          <div className="flex justify-between">
            <span className="font-mono text-slate-400">{r.lat.toFixed(4)}, {r.lng.toFixed(4)}</span>
            <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${STATUS_CLS[r.status]}`}>
              {r.status}
            </span>
          </div>
          {r.description && <p className="mt-1 text-slate-300">{r.description}</p>}
        </li>
      ))}
    </ul>
  );
}

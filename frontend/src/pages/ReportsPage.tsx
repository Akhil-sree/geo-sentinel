import { useEffect, useState } from "react";
import { getReports } from "../api/reports";
import { moderateReport } from "../api/admin";
import { useToast } from "../components/common/Toast";

export default function ReportsPage() {
  const [reports, setReports] = useState<any[]>([]);
  const toast = useToast();

  const load = () => getReports().then(setReports).catch(() => {});
  useEffect(() => { void load(); }, []);

  const moderate = async (id: string, decision: string) => {
    await moderateReport(id, decision);
    toast(`${id.slice(0, 8)}… → ${decision}`, "ok");
    load();
  };

  const chip: Record<string, string> = {
    PENDING: "bg-amber-950 text-amber-400",
    VERIFIED: "bg-emerald-950 text-emerald-400",
    REJECTED: "bg-red-950 text-red-400",
    USED_FOR_TRAINING: "bg-sky-950 text-sky-400",
  };

  return (
   <main className="overflow-y-auto p-4">
      <h1 className="mb-1 text-lg font-semibold">Citizen reports</h1>
      <p className="mb-4 text-xs text-slate-500">
        Moderation required before any training reuse — pending reports are never
        treated as verified ground truth.
      </p>
      <div className="max-w-2xl space-y-2">
        {reports.map((r) => (
          <div key={r.id} className="rounded border border-slate-800 bg-slate-900/60 p-3 text-sm">
            <div className="flex items-center justify-between">
              <b>{r.type || "unclassified"} · {r.severity || "n/a"}</b>
              <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${chip[r.status]}`}>{r.status}</span>
            </div>
            <p className="text-slate-400">{r.description}</p>
            {r.photo_url && <img src={r.photo_url} className="mt-2 max-h-40 rounded" alt="report" />}
            <div className="mt-2 flex items-center gap-2 text-xs text-slate-500">
              <span className="font-mono">{r.lat.toFixed(4)}, {r.lng.toFixed(4)}</span>
              {r.status === "PENDING" && (
                <>
                  <button onClick={() => moderate(r.id, "VERIFIED")}
                    className="rounded bg-emerald-800 px-2 py-0.5">Verify</button>
                  <button onClick={() => moderate(r.id, "REJECTED")}
                    className="rounded bg-red-900 px-2 py-0.5">Reject</button>
                  <button onClick={() => moderate(r.id, "USED_FOR_TRAINING")}
                    className="rounded bg-sky-700 px-2 py-0.5">Use for training</button>
                </>
              )}
            </div>
          </div>
        ))}
        {reports.length === 0 && <p className="text-sm text-slate-500">No reports yet.</p>}
      </div>
    </main>
  );
}

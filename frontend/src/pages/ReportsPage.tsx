import { useEffect, useState } from "react";
import { getReports } from "../api/reports";
import { moderateReport } from "../api/admin";
import { useToast } from "../components/common/Toast";
import { useI18n } from "../lib/i18n";
import { useReportQueue } from "../hooks/useReportQueue";

export default function ReportsPage() {
  const [reports, setReports] = useState<any[]>([]);
  const { queued, syncing, online } = useReportQueue();
  const toast = useToast();
  const { t } = useI18n();

  const load = () => getReports().then(setReports).catch(() => {});
  useEffect(() => { void load(); }, []);

  const moderate = async (id: string, decision: string) => {
    try {
      await moderateReport(id, decision);
      toast(`${id.slice(0, 8)}… → ${decision}`, "ok");
      load();
    } catch (e: any) {
      toast(e?.response?.data?.detail ?? "moderation failed", "err");
    }
  };

  const chip: Record<string, string> = {
    PENDING: "bg-risk-stressed/15 text-risk-stressed",
    VERIFIED: "bg-forest-50 text-forest",
    REJECTED: "bg-risk-critical/15 text-risk-critical",
    USED_FOR_TRAINING: "bg-risk-info/15 text-risk-info",
  };

  return (
   <main className="overflow-y-auto bg-gs-bg p-6">
      <div className="mx-auto max-w-2xl space-y-4">
        <div>
          <h1 className="text-[18px] font-semibold text-gs-text">{t("reports.title")}</h1>
          <p className="mt-1 text-[11px] text-gs-text-secondary">
            {t("reports.subtitle")}
          </p>
          <p className="mt-1 text-[11px] font-medium" role="status"
             aria-label="Offline sync status">
            {!online && <span className="text-risk-stressed">● Offline — reports queue locally</span>}
            {online && syncing && <span className="text-risk-info">● Syncing queued reports…</span>}
            {online && !syncing && queued > 0 && (
              <span className="text-risk-stressed">● {queued} report(s) pending sync</span>)}
            {online && !syncing && queued === 0 && (
              <span className="text-forest">● Online — queue empty</span>)}
          </p>
        </div>
        <div className="space-y-2">
          {reports.map((r) => (
            <div key={r.id} className="rounded-card p-4" style={{
              background: 'rgba(255, 255, 255, 0.52)',
              backdropFilter: 'blur(8px)',
              WebkitBackdropFilter: 'blur(8px)',
              border: '1px solid rgba(214, 208, 196, 0.35)',
              boxShadow: '0 2px 12px rgba(42, 51, 45, 0.05)',
            }}>
              <div className="flex items-center justify-between">
                <b className="text-[12px] text-gs-text">{r.type || "unclassified"} · {r.severity || "n/a"}</b>
                <span className={`rounded px-2 py-0.5 text-[10px] font-medium ${chip[r.status]}`}>{r.status}</span>
              </div>
              <p className="mt-1 text-[11px] text-gs-text-secondary">{r.description}</p>
              {r.photo_url && <img src={r.photo_url} className="mt-2 max-h-40 rounded-card" alt="report" />}
              <div className="mt-2 flex items-center gap-2 text-[10px] text-gs-text-secondary">
                <span className="font-medium">{r.lat.toFixed(4)}, {r.lng.toFixed(4)}</span>
                {r.status === "PENDING" && (
                  <>
                    <button onClick={() => moderate(r.id, "VERIFIED")}
                      className="rounded bg-forest px-2 py-0.5 text-white text-[10px] font-medium">Verify</button>
                    <button onClick={() => moderate(r.id, "REJECTED")}
                      className="rounded bg-risk-critical px-2 py-0.5 text-white text-[10px] font-medium">Reject</button>
                    <button onClick={() => moderate(r.id, "USED_FOR_TRAINING")}
                      className="rounded bg-risk-info px-2 py-0.5 text-white text-[10px] font-medium">Use for training</button>
                  </>
                )}
              </div>
            </div>
          ))}
          {reports.length === 0 && <p className="text-[11px] text-gs-text-secondary">{t("reports.noReports")}</p>}
        </div>
      </div>
    </main>
  );
}

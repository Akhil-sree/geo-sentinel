import { useState } from "react";
import { sendAlert } from "../../api/alerts";

export default function SendButton({ zoneId, severity, onSent }: {
  zoneId: string; severity: string; onSent?: (n: number) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <span className="inline-flex items-center gap-2">
      <button
        disabled={busy}
        aria-label={`Dispatch ${severity} alert for zone ${zoneId} (mock delivery unless live provider configured)`}
        aria-live="polite"
        onClick={async () => {
          setBusy(true);
          setError(null);
          try {
            const res = await sendAlert(zoneId, severity);
            onSent?.(res.sent);
          } catch (e: any) {
            setError(e?.response?.data?.detail ?? "dispatch failed");
          } finally {
            setBusy(false);
          }
        }}
        className="rounded-card bg-risk-critical px-3 py-1.5 text-[11px] font-medium text-white transition hover:bg-risk-critical/90 disabled:opacity-50"
        title="Delivery: logged only (MOCK DELIVERY) unless a live SMS provider is configured"
      >
        {busy ? "Sending…" : "Dispatch (mock)"}
      </button>
      {error && <span role="alert" className="text-[11px] text-risk-critical">{error}</span>}
    </span>
  );
}

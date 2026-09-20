import { useState } from "react";
import { isAlertEligible } from "../../lib/severity";
import { sendAlert } from "../../api/alerts";
import { useToast } from "../common/Toast";
import type { ZoneRisk } from "../../types/risk";

export default function AlertSection({ risk }: { risk: ZoneRisk }) {
  const [lang, setLang] = useState("en");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const toast = useToast();

  const dispatch = async () => {
    setBusy(true);
    try {
      const res = await sendAlert(risk.zone_id, risk.severity, lang);
      setResult(`Sent ${res.sent} message(s) via ${res.provider} (MockSMSProvider)`);
      toast(`Alert dispatched to ${res.sent} recipient(s)`);
    } catch (e: any) {
      toast(e?.response?.data?.detail ?? "dispatch blocked", "err");
    } finally {
      setBusy(false);
    }
  };

  if (!isAlertEligible(risk.severity)) {
    return (
      <p className="text-[12px] text-gs-text-secondary">
        Alert dispatch unavailable — severity below HIGH threshold (enforced server-side as well).
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <select value={lang} onChange={(e) => setLang(e.target.value)}
          className="rounded-card border border-gs-border bg-white p-2 text-[12px] text-gs-text">
          <option value="en">English</option>
          <option value="hi">हिन्दी</option>
        </select>
        <button onClick={dispatch} disabled={busy}
          className="flex-1 rounded-card bg-risk-critical py-2.5 text-[13px] font-semibold text-white transition hover:bg-risk-critical/90 disabled:opacity-50 active:scale-[0.98]">
          {busy ? "Dispatching…" : `Dispatch ${risk.severity} advisory`}
        </button>
      </div>
      <p className="text-[11px] leading-relaxed text-risk-stressed">
        MockSMSProvider — masked numbers, no SMS transmitted. Real deployment requires an
        authorized phone-to-zone directory, DLT-registered sender IDs, and SDMA integration.
        Advisory language only — never evacuation directives.
      </p>
      {result && <p className="text-[12px] text-forest">{result}</p>}
    </div>
  );
}

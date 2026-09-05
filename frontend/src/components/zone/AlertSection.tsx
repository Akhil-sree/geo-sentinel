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
      setResult(`Sent ${res.sent} message(s) via ${res.provider} (MockSMSProvider — demo)`);
      toast(`Alert dispatched to ${res.sent} recipient(s)`);
    } catch (e: any) {
      toast(e?.response?.data?.detail ?? "dispatch blocked", "err");
    } finally {
      setBusy(false);
    }
  };

  if (!isAlertEligible(risk.severity)) {
    return (
      <p className="text-xs text-[#707973]">
        Alert dispatch unavailable — severity below HIGH threshold (gating enforced
        server-side too, not just in this UI).
      </p>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <select value={lang} onChange={(e) => setLang(e.target.value)}
          className="rounded border border-[#d9e2d9] bg-white p-1.5 text-xs text-[#1b1c17]">
          <option value="en">English</option>
          <option value="hi">हिन्दी</option>
        </select>
        <button onClick={dispatch} disabled={busy}
          className="flex-1 rounded bg-[#ba1a1a] py-2 text font-bold text-white disabled:opacity-50">
          {busy ? "Dispatching…" : `🔔 Dispatch ${risk.severity} Advisory (Demo)`}
        </button>
      </div>
      <p className="text-[9px] leading-relaxed text-[#92400e]">
        MockSMSProvider — masked numbers, no SMS transmitted. Real deployment requires an
        authorized phone-to-zone directory, DLT-registered sender IDs, and SDMA integration.
        Advisory language only — never evacuation directives.
      </p>
      {result && <p className="text-xs text-[#04442f]">{result}</p>}
    </div>
  );
}

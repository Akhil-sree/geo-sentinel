import { useState } from "react";
import { isAlertEligible } from "../../lib/severity";
import { sendAlert } from "../../api/alerts";
import { useToast } from "../common/Toast";
import { t, type Lang } from "../../lib/i18n";
import type { ZoneRisk } from "../../types/risk";

const ALERT_LANGUAGES: { value: Lang; label: string; native: string }[] = [
  { value: "en", label: "English", native: "English" },
  { value: "hi", label: "Hindi", native: "\u0939\u093F\u0928\u094D\u0926\u0940" },
  { value: "bn", label: "Bengali", native: "\u09AC\u09BE\u0902\u0997\u09BE" },
  { value: "kha", label: "Khasi", native: "Khasi" },
  { value: "garo", label: "Garo", native: "Garo" },
];

export default function AlertSection({ risk }: { risk: ZoneRisk }) {
  const [lang, setLang] = useState<Lang>("en");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const toast = useToast();

  const dispatch = async () => {
    setBusy(true);
    try {
      const res = await sendAlert(risk.zone_id, risk.severity, lang);
      setResult(`Sent ${res.sent} message(s) via ${res.provider} (MockSMSProvider \u2014 demo)`);
      toast(`Alert dispatched to ${res.sent} recipient(s) in ${ALERT_LANGUAGES.find((l) => l.value === lang)?.native}`);
    } catch (e: any) {
      toast(e?.response?.data?.detail ?? "dispatch blocked", "err");
    } finally {
      setBusy(false);
    }
  };

  if (!isAlertEligible(risk.severity)) {
    return (
      <div className="rounded border border-[#245c45]/20 bg-[#245c45]/5 p-2">
        <p className="text-[9px] text-[#245c45]">
          {t("alertLow")} — severity ({risk.severity}) below HIGH threshold. Alert dispatch gated server-side.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {/* Severity-specific banner */}
      <div className="rounded border p-2" style={{
        borderColor: risk.severity === "VERY_HIGH" ? "#ba1a1a40" : "#ea580c40",
        backgroundColor: risk.severity === "VERY_HIGH" ? "#ba1a1a08" : "#ea580c08",
      }}>
        <p className="text-[9px] font-bold" style={{ color: risk.severity === "VERY_HIGH" ? "#ba1a1a" : "#ea580c" }}>
          {risk.severity === "VERY_HIGH" ? t("alertVeryHigh") : t("alertHigh")}
        </p>
        <p className="text-[8px] text-[#707973]">
          {risk.name}, {risk.district} — Risk: {(risk.risk_score * 100).toFixed(0)}%
        </p>
      </div>

      {/* Language selection */}
      <div>
        <p className="mb-1 text-[8px] font-bold uppercase tracking-wider text-[#707973]">{t("language")}</p>
        <div className="flex gap-1">
          {ALERT_LANGUAGES.map((l) => (
            <button
              key={l.value}
              onClick={() => setLang(l.value)}
              className={`flex-1 rounded border py-1 text-[8px] font-bold transition-colors ${
                lang === l.value
                  ? "border-[#04442f] bg-[#04442f] text-white"
                  : "border-[#d9e2d9] bg-white text-[#404943] hover:bg-[#f0eee6]"
              }`}
            >
              {l.native}
            </button>
          ))}
        </div>
      </div>

      {/* Dispatch button */}
      <button
        onClick={dispatch}
        disabled={busy}
        className="w-full rounded-lg bg-[#ba1a1a] py-2.5 text-[11px] font-bold text-white hover:bg-[#991b1b] disabled:opacity-50 transition-colors shadow-sm"
      >
        {busy ? "Dispatching..." : `🔔 ${t("dispatchAlert")} (${risk.severity})`}
      </button>

      <p className="text-[8px] leading-relaxed text-[#92400e]">
        MockSMSProvider — masked numbers, no SMS transmitted. Advisory language only — never evacuation directives.
        Real deployment requires DLT-registered sender IDs and SDMA integration.
      </p>

      {result && (
        <div className="rounded border border-[#245c45]/20 bg-[#245c45]/5 p-2">
          <p className="text-[9px] font-bold text-[#245c45]">{result}</p>
        </div>
      )}
    </div>
  );
}

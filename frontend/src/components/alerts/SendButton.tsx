// SendButton.tsx — thin wrapper used by ZonePanel (AlertSection already covers
// eligibility gating); kept for direct console use.
import { sendAlert } from "../../api/alerts";

export default function SendButton({ zoneId, severity, onSent }: {
  zoneId: string; severity: string; onSent?: (n: number) => void;
}) {
  return (
    <button onClick={async () => {
      const res = await sendAlert(zoneId, severity);
      onSent?.(res.sent);
    }} className="rounded bg-orange-600 px-3 py-1 text-xs font-semibold">
      Dispatch
    </button>
  );
}

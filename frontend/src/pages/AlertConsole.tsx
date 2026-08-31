import { useEffect, useState } from "react";
import { getAlerts } from "../api/alerts";

export default function AlertConsole() {
  const [alerts, setAlerts] = useState<any[]>([]);
  useEffect(() => { getAlerts().then(setAlerts).catch(() => {}); }, []);

  return (
    <main className="overflow-y-auto p-4">
      <h1 className="mb-1 text-lg font-semibold">Alert audit log</h1>
      <p className="mb-4 text-xs text-slate-500">
        Every dispatched message is persisted — provider, masked recipient, language.
        MockSMSProvider in demo: no SMS actually transmitted.
      </p>
      <div className="max-w-3xl space-y-2">
        {alerts.map((a, i) => (
          <div key={i} className="rounded border border-slate-800 bg-slate-900/60 p-3 text-xs">
            <div className="flex justify-between font-mono text-[10px] text-slate-500">
              <span>{a.at}</span>
              <span>{a.severity} · {a.zone_id} · {a.provider} · {a.lang}</span>
            </div>
            <p className="mt-1 text-slate-300">{a.message}</p>
            <p className="mt-1 text-slate-600">
              to {a.to} ({a.recipient_name}) — {a.status}
            </p>
          </div>
        ))}
        {alerts.length === 0 && <p className="text-sm text-slate-500">No alerts dispatched yet.</p>}
      </div>
    </main>
  );
}

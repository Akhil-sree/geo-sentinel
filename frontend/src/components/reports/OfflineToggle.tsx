import { useState } from "react";
import { useOnlineStatus } from "../../hooks/useOnlineStatus";
import { queueSize } from "../../lib/offline";

/** Demo control: simulate being offline (blocks submit path) + shows queue depth. */
export default function OfflineToggle() {
  const real = useOnlineStatus();
  const [simulatedOffline, setSimulatedOffline] = useState(false);
  const [queued, setQueued] = useState(0);

  const refresh = () => queueSize().then(setQueued);
  const effectiveOnline = real && !simulatedOffline;

  return (
    <div className="flex items-center justify-between rounded border border-slate-800 bg-slate-900/60 p-2 text-xs">
      <label className="flex items-center gap-2 text-slate-400">
        <input type="checkbox" checked={simulatedOffline}
          onChange={(e) => { setSimulatedOffline(e.target.checked); refresh(); }} />
        Simulate offline
      </label>
      <span className={effectiveOnline ? "text-emerald-400" : "text-amber-400"}>
        {effectiveOnline ? "online" : `offline · ${queued} queued`}
      </span>
    </div>
  );
}

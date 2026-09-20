import { useState } from "react";
import { useOnlineStatus } from "../../hooks/useOnlineStatus";
import { queueSize } from "../../lib/offline";

export default function OfflineToggle() {
  const real = useOnlineStatus();
  const [simulatedOffline, setSimulatedOffline] = useState(false);
  const [queued, setQueued] = useState(0);

  const refresh = () => queueSize().then(setQueued);
  const effectiveOnline = real && !simulatedOffline;

  return (
    <div className="flex items-center justify-between rounded-card p-2.5 text-[10px]" style={{
      background: 'rgba(244, 241, 235, 0.65)',
      backdropFilter: 'blur(6px)',
      WebkitBackdropFilter: 'blur(6px)',
      border: '1px solid rgba(214, 208, 196, 0.30)',
    }}>
      <label className="flex items-center gap-2 text-gs-text-secondary">
        <input type="checkbox" checked={simulatedOffline}
          onChange={(e) => { setSimulatedOffline(e.target.checked); refresh(); }}
          className="accent-forest" />
        Simulate offline
      </label>
      <span className={effectiveOnline ? "text-forest font-medium" : "text-risk-stressed font-medium"}>
        {effectiveOnline ? "online" : `offline · ${queued} queued`}
      </span>
    </div>
  );
}

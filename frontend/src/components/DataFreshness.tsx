import { useEffect, useState } from "react";
import { getDataFreshness } from "../api/admin";

export default function DataFreshness() {
  const [data, setData] = useState<any>(null);
  useEffect(() => { getDataFreshness().then(setData).catch(() => {}); }, []);
  if (!data) return null;

  return (
    <div className="rounded-card px-3 py-2 text-[10px]" style={{
      background: 'rgba(245, 247, 243, 0.82)',
      backdropFilter: 'blur(10px)',
      WebkitBackdropFilter: 'blur(10px)',
      border: '1px solid rgba(255, 255, 255, 0.35)',
      boxShadow: '0 2px 10px rgba(42, 51, 45, 0.04)',
    }}>
      {data.mode && !/demo/i.test(data.mode) && (
        <div className="mb-1 font-medium text-gs-text">{data.mode}</div>
      )}
      {data.freshness.map((f: any) => (
        <div key={f.source} className="flex gap-2">
          <span className="text-gs-text-secondary">{f.source}</span>
          <span className={/stale|old|baseline/i.test(f.state)
            ? "text-risk-stressed" : "text-forest"}>{String(f.state).replace(/demo/gi, "Standby")}</span>
        </div>
      ))}
    </div>
  );
}

import { useEffect, useState } from "react";
import { getDataFreshness } from "../api/admin";

export default function DataFreshness() {
  const [data, setData] = useState<any>(null);
  useEffect(() => { getDataFreshness().then(setData).catch(() => {}); }, []);
  if (!data) return null;

  return (
    <div className="rounded border border-slate-800 bg-[#0d1526]/95 px-3 py-2 text-[10px]">
      <div className="mb-1 font-mono font-bold text-slate-300">{data.mode}</div>
      {data.freshness.map((f: any) => (
        <div key={f.source} className="flex gap-2">
          <span className="text-slate-400">{f.source}</span>
          <span className={/stale|old|baseline|demo/i.test(f.state)
            ? "text-amber-400" : "text-emerald-400"}>{f.state}</span>
        </div>
      ))}
    </div>
  );
}

import { useEffect, useState } from "react";
import { getDataFreshness } from "../../api/admin";

export default function DataFreshnessBar() {
  const [data, setData] = useState<any>(null);
  useEffect(() => { getDataFreshness().then(setData).catch(() => {}); }, []);

  return (
    <div className="border-b border-[#d9e2d9] bg-white p-3">
      <p className="mb-1.5 text-[9px] font-bold uppercase tracking-wider text-[#707973]">Data Freshness</p>
      <div className="flex flex-wrap gap-1.5">
        {!data && <span className="text-[10px] text-[#707973]">checking sources…</span>}
        {data?.freshness?.map((f: any) => (
          <span key={f.source} title={f.note}
            className={`rounded px-1.5 py-0.5 text-[9px] font-mono ${
              f.state.startsWith("STALE") || f.state.includes("DEMO")
                ? "bg-[#d97706]/10 text-[#92400e]"
                : "bg-[#245c45]/10 text-[#245c45]"}`}>
            {f.source}: {f.state}
          </span>
        ))}
      </div>
      {data?.mode && <p className="mt-1 text-[8px] text-[#707973]">{data.mode}</p>}
    </div>
  );
}

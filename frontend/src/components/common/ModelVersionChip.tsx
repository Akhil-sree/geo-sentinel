// src/components/common/ModelVersionChip.tsx
export default function ModelVersionChip({ versions }: { versions: any }) {
  return (
    <span className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[9px] text-slate-500"
      title="Served from backend artifacts — RF from training metadata; temporal backend flagged when running on the Mock fallback">
      rf:{versions.rf} · temporal:{versions.mamba} · fusion:{versions.fusion}
    </span>
  );
}

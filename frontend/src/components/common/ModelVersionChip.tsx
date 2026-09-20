export default function ModelVersionChip({ versions }: { versions: any }) {
  return (
    <span className="rounded bg-gs-border/50 px-2 py-0.5 text-[9px] font-medium text-gs-text-secondary"
      title="Served from backend artifacts — RF from training metadata; temporal backend flagged when running on the Mock fallback">
      rf:{versions.rf} · temporal:{versions.mamba} · fusion:{versions.fusion}
    </span>
  );
}

/** Honesty UI: every data layer carries its freshness/quality state verbatim.
 *  Stale sources are labeled stale — never rendered as live. */
export default function FreshnessChip({ label, state }: { label: string; state: string }) {
  const stale = /stale|old|demo/i.test(state);
  return (
    <span className={`rounded px-1.5 py-0.5 text-[10px] font-mono
      ${stale ? "bg-amber-950 text-amber-400" : "bg-emerald-950 text-emerald-400"}`}>
      {label}: {state}
    </span>
  );
}

export default function FreshnessChip({ label, state }: { label: string; state: string }) {
  const stale = /stale|old/i.test(state);
  const cleanState = state.replace(/demo/gi, "standby");
  return (
    <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium
      ${stale ? "bg-risk-stressed/10 text-risk-stressed" : "bg-forest-50 text-forest"}`}>
      {label}: {cleanState}
    </span>
  );
}

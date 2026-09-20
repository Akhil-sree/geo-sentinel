function phase(t: number): { label: string; cls: string } {
  if (t < 48) return { label: "Baseline", cls: "bg-white/10 text-white/60" };
  if (t < 96) return { label: "Build-up", cls: "bg-risk-info/20 text-sky-300" };
  if (t < 140) return { label: "Intense", cls: "bg-risk-stressed/20 text-amber-300" };
  return { label: "Peak", cls: "bg-risk-critical/20 text-red-300" };
}

export default function PhaseBadge({ t }: { t: number }) {
  const p = phase(t);
  return <span className={`rounded px-2 py-0.5 text-[10px] font-medium ${p.cls}`}>{p.label}</span>;
}

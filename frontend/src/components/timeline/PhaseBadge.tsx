function phase(t: number): { label: string; cls: string } {
  if (t < 48) return { label: "BASELINE", cls: "bg-slate-800 text-slate-400" };
  if (t < 96) return { label: "BUILD-UP", cls: "bg-sky-950 text-sky-400" };
  if (t < 140) return { label: "INTENSE", cls: "bg-orange-950 text-orange-400" };
  return { label: "PEAK", cls: "bg-red-950 text-red-400" };
}

export default function PhaseBadge({ t }: { t: number }) {
  const p = phase(t);
  return <span className={`rounded px-2 py-0.5 font-mono text-[10px] font-bold ${p.cls}`}>{p.label}</span>;
}

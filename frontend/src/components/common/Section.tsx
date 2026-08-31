// Section.tsx — collapsible panel section, open by default
import { useState } from "react";

export default function Section({ title, children, defaultOpen = true }: {
  title: string; children: React.ReactNode; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/40">
      <button onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-3 py-2 text-left">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">{title}</span>
        <span className="text-slate-600">{open ? "▾" : "▸"}</span>
      </button>
      {open && <div className="border-t border-slate-800 p-3">{children}</div>}
    </div>
  );
}

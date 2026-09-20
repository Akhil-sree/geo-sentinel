import { useState } from "react";

export default function Section({ title, children, defaultOpen = true }: {
  title: string; children: React.ReactNode; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-card" style={{
  background: 'rgba(255, 255, 255, 0.55)',
  backdropFilter: 'blur(4px)',
  WebkitBackdropFilter: 'blur(4px)',
  border: '1px solid rgba(255, 255, 255, 0.30)',
  boxShadow: '0 2px 10px rgba(15, 35, 27, 0.04)',
    }}>
      <button onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-3.5 py-2.5 text-left transition hover:bg-gs-bg/50">
        <span className="text-[11px] font-medium text-gs-text">{title}</span>
        <span className="text-gs-text-secondary text-[10px]">{open ? "▾" : "▸"}</span>
      </button>
      {open && <div className="border-t border-gs-border/50 p-3.5">{children}</div>}
    </div>
  );
}

import { useEffect } from "react";

export function Modal({ open, onClose, title, children }: {
  open: boolean; onClose: () => void; title: string; children: React.ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[1000] grid place-items-center bg-black/60"
         onClick={onClose} role="dialog" aria-modal="true" aria-label={title}>
      <div className="w-full max-w-md rounded-xl border border-slate-700 bg-[#0d1526] p-5 shadow-2xl"
           onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-bold tracking-wide">{title}</h2>
          <button onClick={onClose} aria-label="close" className="text-slate-500 hover:text-slate-300">✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}

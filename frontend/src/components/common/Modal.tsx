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
    <div className="fixed inset-0 z-[1000] grid place-items-center bg-black/50 backdrop-blur-sm"
         onClick={onClose} role="dialog" aria-modal="true" aria-label={title}>
      <div className="w-full max-w-md rounded-card p-5 shadow-2xl" style={{
        background: 'rgba(245, 247, 243, 0.92)',
        backdropFilter: 'blur(14px)',
        WebkitBackdropFilter: 'blur(14px)',
        border: '1px solid rgba(255, 255, 255, 0.45)',
        boxShadow: '0 14px 40px rgba(0, 0, 0, 0.25)',
      }}
           onClick={(e) => e.stopPropagation()}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-[13px] font-semibold text-gs-text">{title}</h2>
          <button onClick={onClose} aria-label="close" className="text-gs-text-secondary hover:text-gs-text transition">✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}

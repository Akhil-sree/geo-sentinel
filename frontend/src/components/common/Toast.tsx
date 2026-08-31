import { createContext, useCallback, useContext, useState } from "react";

type ToastKind = "ok" | "err";
interface Toast { id: number; msg: string; kind: ToastKind; }

const ToastCtx = createContext<(msg: string, kind?: ToastKind) => void>(() => {});

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const push = useCallback((msg: string, kind: ToastKind = "ok") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, msg, kind }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3500);
  }, []);

  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="fixed bottom-4 right-4 z-[1100] space-y-2">
        {toasts.map((t) => (
          <div key={t.id}
            className={`rounded px-4 py-2 text-xs font-medium shadow-lg
              ${t.kind === "ok" ? "bg-emerald-800 text-emerald-100" : "bg-red-800 text-red-100"}`}>
            {t.msg}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export const useToast = () => useContext(ToastCtx);

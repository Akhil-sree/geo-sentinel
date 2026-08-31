import { useGeolocation } from "../../hooks/useGeolocation";

export default function GpsCapture({ onFix }: {
  onFix: (f: { lat: number; lng: number } | null) => void;
}) {
  const { fix, busy, error, acquire } = useGeolocation();

  const handle = async () => {
    const f = await acquire();          // ← fresh value returned, not stale state
    onFix(f);
  };

  return (
    <div>
      <label className="block text-xs font-semibold text-slate-400">Location</label>
      <div className="mt-1 flex items-center gap-2">
        <button type="button" onClick={handle} disabled={busy}
          className="rounded bg-slate-800 px-3 py-1.5 text-xs disabled:opacity-50">
          {busy ? "Acquiring…" : "📍 Get GPS"}
        </button>
        {fix && (
          <span className="font-mono text-xs text-slate-300">
            {fix.lat.toFixed(5)}, {fix.lng.toFixed(5)} <span className="text-slate-500">±{fix.accuracy}m</span>
          </span>
        )}
      </div>
      {error && <p className={`mt-1 text-xs ${fix ? "text-amber-400" : "text-red-400"}`}>{error}</p>}
    </div>
  );
}

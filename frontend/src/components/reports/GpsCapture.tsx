import { useGeolocation } from "../../hooks/useGeolocation";

export default function GpsCapture({ onFix }: {
  onFix: (f: { lat: number; lng: number } | null) => void;
}) {
  const { fix, busy, error, acquire } = useGeolocation();

  const handle = async () => {
    const f = await acquire();
    onFix(f);
  };

  return (
    <div>
      <label className="block text-[10px] font-medium text-gs-text-secondary">Location</label>
      <div className="mt-1 flex items-center gap-2">
        <button type="button" onClick={handle} disabled={busy}
          className="rounded-card bg-gs-bg px-3 py-1.5 text-[11px] font-medium text-gs-text border border-gs-border transition hover:bg-gs-border/30 disabled:opacity-50">
          {busy ? "Acquiring…" : "📍 Get GPS"}
        </button>
        {fix && (
          <span className="text-[11px] text-gs-text">
            {fix.lat.toFixed(5)}, {fix.lng.toFixed(5)} <span className="text-gs-text-secondary">±{fix.accuracy}m</span>
          </span>
        )}
      </div>
      {error && <p className={`mt-1 text-[10px] ${fix ? "text-risk-stressed" : "text-risk-critical"}`}>{error}</p>}
    </div>
  );
}

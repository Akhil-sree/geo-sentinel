import { useCallback, useState } from "react";
import { getGps, accuracyWarning, type GpsFix } from "../lib/gps";

export function useGeolocation() {
  const [fix, setFix] = useState<GpsFix | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const acquire = useCallback(async (): Promise<GpsFix | null> => {
    setBusy(true); setError(null);
    try {
      const f = await getGps();
      setFix(f);
      setError(accuracyWarning(f.accuracy));
      return f;
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unable to acquire location");
      return null;
    }
    finally { setBusy(false); }
  }, []);

  return { fix, busy, error, acquire };
}

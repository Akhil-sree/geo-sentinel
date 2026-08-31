import { useEffect, useState } from "react";
import { useUIStore } from "../store/uiStore";
import { getZoneHistory } from "../api/risk";
import type { RiskHistoryPoint } from "../types/risk";

/** Selected zone + its persisted risk history (from risk_scores table). */
export function useZoneSelection() {
  const { selectedZoneId, selectZone } = useUIStore();
  const [history, setHistory] = useState<RiskHistoryPoint[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selectedZoneId) { setHistory([]); return; }
    setLoading(true);
    getZoneHistory(selectedZoneId)
      .then(setHistory)
      .catch(() => setHistory([]))
      .finally(() => setLoading(false));
  }, [selectedZoneId]);

  return { selectedZoneId, selectZone, history, loading };
}

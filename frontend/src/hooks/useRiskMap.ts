import { useEffect, useState } from "react";

import { getRiskMap } from "../api/risk";
import type { ZoneRisk } from "../types/risk";

export function useRiskMap(t: number) {
  const [risks, setRisks] = useState<ZoneRisk[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    setLoading(true);

    getRiskMap(t)
      .then((r) => {
        if (!cancelled) {
          setRisks(r);
          setError(null);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError("Risk service unreachable");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [t]);

  return {
    risks,
    loading,
    error,
  };
}
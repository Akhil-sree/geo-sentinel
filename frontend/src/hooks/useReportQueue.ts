import { useCallback, useEffect, useState } from "react";
import { useOnlineStatus } from "./useOnlineStatus";
import { enqueueReport, flushQueue, queueSize, type QueuedReport } from "../lib/offline";
import { submitReportRequest } from "../api/reports";

export function useReportQueue() {
  const online = useOnlineStatus();
  const [queued, setQueued] = useState(0);
  const [syncing, setSyncing] = useState(false);

  const refresh = useCallback(() => { queueSize().then(setQueued); }, []);
  useEffect(refresh, [refresh]);

  // auto-flush whenever connectivity returns
  useEffect(() => {
    if (!online || syncing) return;
    setSyncing(true);
    flushQueue(submitReportRequest)
      .then(refresh)
      .catch(() => {})        // failed items stay queued with attempts++
      .finally(() => setSyncing(false));
  }, [online, syncing, refresh]);

  const submit = useCallback(async (rep: QueuedReport): Promise<boolean> => {
    if (!online) {
      await enqueueReport(rep);
      refresh();
      return false;           // queued, not submitted
    }
    try {
      await submitReportRequest(rep);
      return true;
    } catch {
      await enqueueReport(rep);   // network blip mid-submit → queue
      refresh();
      return false;
    }
  }, [online, refresh]);

  return { submit, queued, online, syncing, refresh };
}

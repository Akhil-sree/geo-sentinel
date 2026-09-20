import { get, set } from "idb-keyval";

const QUEUE_KEY = "gs_report_queue";
let memoryQueue: QueuedReport[] = [];

export interface QueuedReport {
  id: string;
  payload: Record<string, string | number>;
  photoBlob?: Blob | null;
  queuedAt: string;
  attempts: number;
}

/** Sync lifecycle for the queue UI: OFFLINE → SYNCING → SYNCED / FAILED. */
export type SyncStatus = "OFFLINE" | "SYNCING" | "SYNCED" | "FAILED";

export function describeSync(online: boolean, pending: number, lastError: boolean): SyncStatus {
  if (!online && pending > 0) return "OFFLINE";
  if (!online) return "OFFLINE";
  if (pending > 0 && lastError) return "FAILED";
  if (pending > 0) return "SYNCING";
  return "SYNCED";
}

// IndexedDB is durable storage in browsers. The fallback supports constrained
// webviews and prevents the offline workflow from crashing when it is absent.
const canUseIndexedDb = () => typeof indexedDB !== "undefined";

async function loadQueue(): Promise<QueuedReport[]> {
  if (!canUseIndexedDb()) return [...memoryQueue];
  return (await get<QueuedReport[]>(QUEUE_KEY)) ?? [];
}

async function saveQueue(queue: QueuedReport[]): Promise<void> {
  if (!canUseIndexedDb()) {
    memoryQueue = [...queue];
    return;
  }
  await set(QUEUE_KEY, queue);
}

export async function enqueueReport(rep: QueuedReport): Promise<void> {
  const queue = await loadQueue();
  queue.push(rep);
  await saveQueue(queue);
}

export async function queueSize(): Promise<number> {
  return (await loadQueue()).length;
}

export async function flushQueue(
  send: (r: QueuedReport) => Promise<unknown>,
): Promise<number> {
  const queue = await loadQueue();
  const remaining: QueuedReport[] = [];

  for (const report of queue) {
    try {
      await send(report);
    } catch {
      remaining.push({ ...report, attempts: report.attempts + 1 });
    }
  }

  await saveQueue(remaining);
  return queue.length - remaining.length;
}

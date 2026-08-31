import { api } from "./client";
import type { QueuedReport } from "../lib/offline";

/** Shared sender used by both the online path and the offline queue flush.
 *  Photo, if present, goes to the separate media endpoint after the report
 *  itself is accepted. */
export async function submitReportRequest(rep: QueuedReport): Promise<void> {
  await api.post("/reports", { id: rep.id, ...rep.payload }, { headers: { "Content-Type": "application/json" } });
  if (rep.photoBlob) {
    const fd = new FormData();
    fd.append("file", rep.photoBlob, "photo.jpg");
    await api.post(`/reports/${rep.id}/media`, fd,
      { headers: { "Content-Type": "multipart/form-data" } });
  }
}

export const getReports = () => api.get("/reports").then((r) => r.data);

export const syncReport = (id: string) =>
  api.post(`/reports/${id}/sync`).then((r) => r.data);

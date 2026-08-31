import { api } from "./client";

export const getDataFreshness = () => api.get("/admin/data").then((r) => r.data);
export const getModelMetrics = () => api.get("/admin/model/metrics").then((r) => r.data);

export const moderateReport = (id: string, decision: string) =>
  api.post(`/admin/moderate/${id}`, null, { params: { decision } }).then((r) => r.data);
//                                              ^^^ was `reportId` — undefined variable

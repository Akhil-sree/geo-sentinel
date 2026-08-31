import { api } from "./client";

export const sendAlert = (zone_id: string, severity: string, lang = "en") =>
  api.post("/alerts/send", { zone_id, severity, lang }).then((r) => r.data);

export const getAlerts = () => api.get("/alerts").then((r) => r.data);

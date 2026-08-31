import { api } from "./client";
import type { ZoneRisk, RiskHistoryPoint } from "../types/risk";

export const getRiskMap = (t: number) =>
  api.get<ZoneRisk[]>("/risk/map", { params: { t } }).then((r) => r.data);

export const getZoneHistory = (zoneId: string) =>
  api.get<RiskHistoryPoint[]>(`/risk/${zoneId}/history`).then((r) => r.data);

export const getZoneRainfall = (zoneId: string) =>
  api.get(`/risk/${zoneId}/rainfall`).then((r) => r.data);

export const getZoneExplanation = (zoneId: string, t: number) =>
  api.get(`/risk/${zoneId}/explanation`, { params: { t } }).then((r) => r.data);

export const getZoneSAR = (zoneId: string) =>
  api.get(`/risk/${zoneId}/satellite`).then((r) => r.data);

export const getModelStatus = () =>
  api.get("/risk/model/status").then((r) => r.data);

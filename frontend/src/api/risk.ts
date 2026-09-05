import { api } from "./client";
import type { ZoneRisk, RiskHistoryPoint, TrajectoryPoint, Hotspot, SimulationResult, IntensificationResult, ZoneEvidence } from "../types/risk";

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

export const getRiskTrajectory = (zoneId: string) =>
  api.get<{ trajectory: TrajectoryPoint[]; interpretation: string }>(
    `/risk/${zoneId}/trajectory`
  ).then((r) => r.data);

export const getHotspotRanking = (t: number) =>
  api.get<{ hotspots: Hotspot[]; total: number; analyzed_at: string }>(
    "/risk/hotspots", { params: { t } }
  ).then((r) => r.data);

export const postScenarioSimulation = (params: {
  multiplier: number;
  continued_hours: number;
  t: number;
}) =>
  api.post<{ scenario: any; results: SimulationResult[]; warning: string }>(
    "/risk/simulation", params
  ).then((r) => r.data);

export const getRiskIntensification = (t: number) =>
  api.get<{ intensification: IntensificationResult[] }>(
    "/risk/intensification", { params: { t } }
  ).then((r) => r.data);

export const getZoneEvidence = (zoneId: string, t: number) =>
  api.get<ZoneEvidence>(`/risk/${zoneId}/evidence`, { params: { t } }).then((r) => r.data);

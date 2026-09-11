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

export interface CellData {
  lat: number;
  lng: number;
  static_score?: number;
  risk_score: number;
  severity?: string;
  slope_state: string;
  slope_state_color: string;
  stress_score: number;
  escalated?: boolean;
}

export const getCellGrid = (zoneId: string, t: number, resolution = 20) =>
  api.get<{ zone_id: string; name: string; cell_count: number; cells: CellData[] }>(
    `/risk/${zoneId}/cell-grid`, { params: { t, resolution } }
  ).then((r) => r.data);

export const getTemporalCellGrid = (zoneId: string, resolution = 16) =>
  api.get<{ zone_id: string; name: string; timesteps: { t: number; label: string; cells: CellData[] }[] }>(
    `/risk/${zoneId}/cell-grid/temporal`, { params: { resolution } }
  ).then((r) => r.data);

export interface ForecastPoint {
  hours_ahead: number;
  projected_rainfall_24h: number;
  projected_rainfall_72h: number;
  projected_soil_moisture: number;
  projected_risk: number;
  projected_severity: string;
  slope_state: string;
  slope_state_label: string;
  slope_state_color: string;
  escalated: boolean;
  rainfall_intensity: string;
  rainfall_color: string;
}

export interface ForecastResult {
  zone_id: string;
  name: string;
  current_risk: number;
  current_severity: string;
  forecasts: ForecastPoint[];
  verdict: string;
  verdict_color: string;
  confidence_note: string;
}

export const getWeatherForecast = (zoneId: string, t: number) =>
  api.get<ForecastResult>(`/risk/${zoneId}/forecast`, { params: { t } }).then((r) => r.data);

export interface EmergencyPriority {
  zone_id: string;
  name: string;
  district: string;
  risk_score: number;
  severity: string;
  slope_state: string;
  slope_state_label: string;
  slope_state_color: string;
  escalated: boolean;
  population: number;
  road_proximity: number;
  urgency_score: number;
  tier: string;
  tier_color: string;
  response_time: string;
  evac_status: string;
  evac_color: string;
  rank: number;
}

export const getEmergencyPriorities = (t: number) =>
  api.get<{ priorities: EmergencyPriority[]; total: number; analyzed_at: string }>(
    "/risk/emergency-priorities", { params: { t } }
  ).then((r) => r.data);

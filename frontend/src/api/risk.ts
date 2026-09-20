import { api } from "./client";
import type {
  ZoneRisk, RiskHistoryPoint, TrajectoryPoint, Hotspot,
  SimulationResult, IntensificationResult, ZoneEvidence,
  CellGridResponse, TemporalCellGridResponse, WeatherForecast,
  EmergencyPriority, SoilMoistureResponse,
} from "../types/risk";

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

export interface ProviderState {
  source: string;
  freshness: string;
  quality: string;
  is_live: boolean;
  is_simulated: boolean;
  observed_at: string | null;
  soil_moisture_source?: string;
  soil_moisture_status?: string;
}

export const getDataStatus = () =>
  api.get<{
    mode: string;
    providers: ProviderState[];
    models: any;
    delivery: Record<string, string>;
  }>("/data-status").then((r) => r.data);

export const getWorkerStatus = () =>
  api.get("/worker-status").then((r) => r.data);

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

export const getCellGrid = (zoneId: string, t: number, resolution: number = 20, mode: string = "observed") =>
  api.get<CellGridResponse>(`/risk/${zoneId}/cell-grid`, { params: { t, resolution, mode } }).then((r) => r.data);

export const getTemporalCellGrid = (zoneId: string, resolution: number = 12, mode: string = "observed") =>
  api.get<TemporalCellGridResponse>(`/risk/${zoneId}/cell-grid/temporal`, { params: { resolution, mode } }).then((r) => r.data);

export const getWeatherForecast = (zoneId: string, t: number) =>
  api.get<WeatherForecast>(`/risk/${zoneId}/forecast`, { params: { t } }).then((r) => r.data);

export const getEmergencyPriorities = (t: number) =>
  api.get<{ priorities: EmergencyPriority[]; total: number; analyzed_at: string }>(
    "/risk/emergency-priorities", { params: { t } }
  ).then((r) => r.data);

export const getSoilMoisture = (zoneId: string) =>
  api.get<SoilMoistureResponse>(`/risk/${zoneId}/soil-moisture`).then((r) => r.data);

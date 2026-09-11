import { api } from "./client";

export interface RoadSegment {
  id: number;
  name: string;
  from_zone: string;
  to_zone: string;
  road_type: string;
  length_km: number;
  status: "OPEN" | "BLOCKED" | "DAMAGED" | "UNDER_REPAIR";
  blockage_reason: string | null;
  last_updated: string | null;
  reported_by: string;
  latitude: number | null;
  longitude: number | null;
}

export interface RoadStatusResult {
  roads: RoadSegment[];
  total: number;
  blocked: number;
  open: number;
  summary: string;
}

export interface WeatherOverviewItem {
  zone_id: string;
  name: string;
  district: string;
  rainfall_24h: number;
  rainfall_72h: number;
  soil_moisture: number;
  risk_score: number;
  severity: string;
  risk_level: string;
  risk_color: string;
  message: string;
  escalated: boolean;
}

export interface WeatherOverviewResult {
  forecasts: WeatherOverviewItem[];
  total: number;
  extreme_count: number;
  high_count: number;
  analyzed_at: string;
}

export interface EmergencyTask {
  id: number;
  zone_id: string;
  task_type: string;
  title: string;
  description: string;
  priority: string;
  status: string;
  assigned_team: string | null;
  estimated_time: string | null;
  created_at: string | null;
  completed_at: string | null;
}

export interface EmergencyTasksResult {
  tasks: EmergencyTask[];
  total: number;
  critical_pending: number;
  in_progress: number;
  completed: number;
}

export interface SeveritySummaryItem {
  zone_id: string;
  name: string;
  district: string;
  risk_score: number;
  severity: string;
  escalated: boolean;
  population: number;
  slope: number;
  elevation: number;
  road_proximity: number;
  rainfall_24h: number;
  soil_moisture: number;
}

export interface SeveritySummaryResult {
  summary: Record<string, number>;
  zones: SeveritySummaryItem[];
  total_zones: number;
  total_population: number;
  exposed_population: number;
  escalated_count: number;
  analyzed_at: string;
}

export const getRoadSegments = () =>
  api.get<RoadStatusResult>("/roads").then((r) => r.data);

export const getWeatherOverview = (t: number = 24) =>
  api.get<WeatherOverviewResult>("/weather/overview", { params: { t } }).then((r) => r.data);

export const getEmergencyTasks = () =>
  api.get<EmergencyTasksResult>("/emergency/tasks").then((r) => r.data);

export const getSeveritySummary = () =>
  api.get<SeveritySummaryResult>("/risk/severity-summary").then((r) => r.data);

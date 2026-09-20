import { api } from "./client";
import type {
  RoadSegment, WeatherOverview, EmergencyTask, SeveritySummary,
  EvacuationRoute, RouteNetwork, ZoneListItem,
  VisionObservation, VisionObservationRecord, CorroborationResult, VisionModelStatus,
} from "../types/risk";

// ── Road GIS ──

export interface RoadGeoJSON {
  type: "FeatureCollection";
  features: RoadFeature[];
  metadata?: {
    source?: string;
    extraction_date?: string;
    aoi?: { min_lon: number; min_lat: number; max_lon: number; max_lat: number };
    crs?: string;
    total_features?: number;
    highway_classes?: Record<string, number>;
    categories?: Record<string, number>;
  };
}

export interface RoadFeature {
  type: "Feature";
  geometry: {
    type: "LineString" | "MultiLineString";
    coordinates: number[][][] | number[][];
  };
  properties: {
    road_id: number;
    highway: string;
    category: string;
    name: string;
    ref: string;
    surface: string;
    oneway: string;
    bridge: string;
    tunnel: string;
    maxspeed: string;
    lanes: string;
  };
}

export interface NearestRoadResult {
  road_id?: number;
  name?: string;
  ref?: string;
  highway?: string;
  category?: string;
  surface?: string;
  distance_m?: number;
  nearest_point?: { lng: number; lat: number };
  error?: string;
}

export const getRoadsGeoJSON = (category?: string) =>
  api.get<RoadGeoJSON>("/roads/geojson", { params: category ? { category } : {} }).then((r) => r.data);

export const findNearestRoad = (lat: number, lng: number) =>
  api.get<NearestRoadResult>("/roads/nearest", { params: { lat, lng } }).then((r) => r.data);

export const getRoads = () =>
  api.get<{ roads: RoadSegment[]; total: number; blocked: number; open: number; summary: string }>(
    "/roads"
  ).then((r) => r.data);

export const getWeatherOverview = (t: number) =>
  api.get<WeatherOverview>("/weather/overview", { params: { t } }).then((r) => r.data);

export const getEmergencyTasks = () =>
  api.get<{ tasks: EmergencyTask[]; total: number; critical_pending: number; in_progress: number; completed: number }>(
    "/emergency/tasks"
  ).then((r) => r.data);

export const getSeveritySummary = (t: number) =>
  api.get<SeveritySummary>("/risk/severity-summary", { params: { t } }).then((r) => r.data);

// ── Routing ──

export const optimizeRoute = (source: string, target: string, mode: string = "response", t: number = 96) =>
  api.get<EvacuationRoute>("/routes/optimize", { params: { source, target, mode, t } }).then((r) => r.data);

export const getAllRoutesFrom = (source: string, mode: string = "response", t: number = 96) =>
  api.get<{ source: string; source_name: string; mode: string; routes: EvacuationRoute[]; total: number }>(
    "/routes/all-from", { params: { source, mode, t } }
  ).then((r) => r.data);

export const recalculateRoute = (source: string, target: string, mode: string = "response", t: number = 96) =>
  api.post<EvacuationRoute>("/routes/recalculate", { source, target, mode, t }).then((r) => r.data);

export const getRouteNetwork = () =>
  api.get<RouteNetwork>("/routes/network").then((r) => r.data);

export const getZonesForRouting = () =>
  api.get<{ zones: ZoneListItem[] }>("/zones/list").then((r) => r.data);

// ── Vision / Observation Intelligence ──

export const analyzeVisionImage = (
  file: File,
  reportId?: string,
  latitude?: number,
  longitude?: number,
  zoneId?: string,
) => {
  const form = new FormData();
  form.append("file", file);
  if (reportId) form.append("report_id", reportId);
  if (latitude != null) form.append("latitude", String(latitude));
  if (longitude != null) form.append("longitude", String(longitude));
  if (zoneId) form.append("zone_id", zoneId);
  return api.post<{ observation_id: number } & VisionObservation>(
    "/vision/analyze", form,
    { headers: { "Content-Type": "multipart/form-data" }, timeout: 60000 }
  ).then((r) => r.data);
};

export const getVisionObservations = (limit: number = 50) =>
  api.get<{ observations: VisionObservationRecord[]; total: number }>(
    "/vision/observations", { params: { limit } }
  ).then((r) => r.data);

export const getVisionObservation = (id: number) =>
  api.get<VisionObservationRecord>(`/vision/observations/${id}`).then((r) => r.data);

export const getVisionReportObservations = (reportId: string) =>
  api.get<{ report_id: string; observations: VisionObservationRecord[]; total: number }>(
    `/vision/reports/${reportId}`
  ).then((r) => r.data);

export const getVisionModelStatus = () =>
  api.get<VisionModelStatus>("/vision/model/status").then((r) => r.data);

export const getVisionCorroboration = (zoneId: string) =>
  api.get<CorroborationResult>(`/vision/corroboration/${zoneId}`).then((r) => r.data);

// ── Rescue / Safe Zones ──

export interface SafeZone {
  id: string;
  name: string;
  lat: number;
  lng: number;
  type: string;
  district: string;
  description: string;
  is_demo: boolean;
  demo_label?: string;
}

export interface RescueEndpoint {
  lat: number;
  lng: number;
  id?: string;
  name?: string;
  type?: string;
  is_demo?: boolean;
}

export interface RescueRouteOption {
  id: string;
  name: string;
  lat: number;
  lng: number;
  distance_km: number;
  eta_min: number;
  type?: string;
  is_demo?: boolean;
}

export interface RescueRouteResult {
  status?: string;
  route_available: boolean;
  origin?: RescueEndpoint | null;
  destination?: RescueEndpoint | null;
  algorithm?: string | null;
  geometry: { type: string; coordinates: number[][] };
  /** Backend alias: exact route path as [[lat, lng], ...] — prefer for Leaflet. */
  route_geometry?: number[][];
  /** Ranked reachable alternatives (auto-select mode only). */
  options?: RescueRouteOption[];
  distance_km: number;
  eta_min?: number;
  eta_basis?: string | null;
  segments: any[];
  roads_used?: any[];
  blocked_avoided: any[];
  roads_avoided?: any[];
  road_count?: number;
  exposure?: { weighted: boolean; note: string };
  origin_snap_m?: number | null;
  destination_snap_m?: number | null;
  explanation: any;
  demo_labels?: string[];
  // Local display names (zone labels); never sent to the backend.
  originName?: string;
  destName?: string;
}

export const getSafeZones = () =>
  api.get<{ safe_zones: SafeZone[]; total?: number }>("/rescue/safe-zones").then((r) => r.data);

export const getRescueRoute = (origin_lat: number, origin_lng: number, destination_lat?: number, destination_lng?: number) =>
  api.post<RescueRouteResult>("/rescue/route", {
    origin_lat, origin_lng, destination_lat, destination_lng,
  }).then((r) => r.data);

export const getBlockedRoads = () =>
  api.get<{ blocked_road_ids: number[]; total: number }>("/rescue/blocked-roads").then((r) => r.data);

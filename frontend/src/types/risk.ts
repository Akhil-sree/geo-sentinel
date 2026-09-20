export type Severity = "LOW" | "MODERATE" | "HIGH" | "VERY_HIGH";

export type SlopeState = "STABLE" | "STRESSED" | "DEGRADING" | "CRITICAL";

export type TrajectoryInterpretation =
  | "RAPIDLY_INTENSIFYING"
  | "GRADUALLY_INCREASING"
  | "DECREASING"
  | "STABLE"
  | "VARIABLE"
  | "NO_DATA";

export interface Driver { factor: string; impact: number; }

export interface ZoneRisk {
  zone_id: string; name: string; district: string;
  static_score: number; dynamic_score: number;
  risk_score: number; severity: Severity;
  escalated: boolean; confidence: number;
  rainfall_24h: number; rainfall_72h: number;
  rainfall_7d: number; rainfall_slope: number;
  soil_moisture: number;
  drivers: Driver[]; summary: string;
  model_versions: { rf: string; mamba: string; fusion: string };
  sim_time: string;
  slope_state?: SlopeState;
  slope_state_label?: string;
  slope_state_color?: string;
  slope_stress_score?: number;
}

export interface RiskHistoryPoint {
  timestamp: string; risk_score: number; static: number;
  dynamic: number; severity: Severity; escalated: boolean;
}

export interface TrajectoryPoint {
  timestamp: string;
  risk_score: number;
  static: number;
  dynamic: number;
  severity: Severity;
  escalated: boolean;
  slope_state: SlopeState;
  slope_state_label: string;
  slope_state_color: string;
}

export interface Hotspot {
  zone_id: string;
  name: string;
  district: string;
  risk_score: number;
  severity: Severity;
  static_score: number;
  dynamic_score: number;
  rainfall_24h: number;
  rainfall_72h: number;
  soil_moisture: number;
  escalated: boolean;
  sar_change_score: number | null;
  trajectory_interpretation: TrajectoryInterpretation;
  hotspot_score: number;
  classification: string;
  trend: string;
  priority: string;
  rank: number;
}

export interface SimulationResult {
  zone_id: string;
  name: string;
  current_risk: number;
  current_severity: Severity;
  simulated_risk: number;
  simulated_severity: Severity;
  slope_state: SlopeState;
  slope_state_label: string;
  slope_state_color: string;
  rainfall_change: string;
  continued_hours: number;
  escalated: boolean;
}

export interface IntensificationResult {
  zone_id: string;
  name: string;
  current_risk: number;
  previous_risk: number | null;
  change: number;
  rate: string;
  color: string;
  severity: Severity;
}

export interface ZoneEvidence {
  zone_id: string;
  name: string;
  district: string;
  risk_score: number;
  severity: Severity;
  static_score: number;
  dynamic_score: number;
  slope_state: { state: SlopeState; label: string; color: string; stress_score: number };
  rainfall: { "24h": number; "72h": number; "7d": number; slope: number };
  soil_moisture: number;
  sar: { acquisition_date: string; previous_acquisition_date: string; change_score: number; honesty_note: string } | null;
  terrain: {
    slope: number; elevation: number; ruggedness: number; population: number;
    dem_observed?: {
      status: string; source: string; resolution_m: number;
      elevation_m: number; slope_deg: number; aspect_deg: number;
      ruggedness_m: number; relief_m: number; curvature: number | null;
      curvature_kind: string; note: string;
    } | null;
  } | null;
  drivers: Driver[];
  explanation: { factors: string[]; conclusion: string; recommended_action: string };
  history?: { event_date: string | null; type: string; source: string }[];
  vulnerable_roads?: { name: string; status: string; blockage_reason: string | null; length_km: number }[];
  active_alerts?: { severity: string; status: string; at: string | null }[];
  freshness?: {
    rainfall?: { observed_at: string | null; source: string | null; quality: string | null };
    soil_moisture?: { observed_at: string | null; source: string | null; quality: string | null };
  };
  model_versions: { rf: string; mamba: string; fusion: string };
  sim_time: string;
}

export interface CellGridCell {
  lat: number;
  lng: number;
  static_score: number;
  risk_score: number;
  severity: Severity;
  slope_state: SlopeState;
  slope_state_color: string;
  stress_score: number;
  escalated: boolean;
}

export interface CellGridResponse {
  zone_id: string;
  name: string;
  cell_count: number;
  resolution: number;
  cell_method?: string;
  demo?: boolean;
  cells: CellGridCell[];
}

export interface TemporalCellGridTimestep {
  t: number;
  label: string;
  cells: { lat: number; lng: number; risk_score: number; slope_state: SlopeState; slope_state_color: string; stress_score: number }[];
}

export interface TemporalCellGridResponse {
  zone_id: string;
  name: string;
  cell_method?: string;
  demo?: boolean;
  timesteps: TemporalCellGridTimestep[];
}

export interface ForecastPoint {
  hours_ahead: number;
  projected_rainfall_24h: number;
  projected_rainfall_72h: number;
  projected_soil_moisture: number;
  projected_risk: number;
  projected_severity: Severity;
  slope_state: SlopeState;
  slope_state_label: string;
  slope_state_color: string;
  escalated: boolean;
  rainfall_intensity: string;
  rainfall_color: string;
}

export interface WeatherForecast {
  zone_id: string;
  name: string;
  current_risk: number;
  current_severity: Severity;
  forecasts: ForecastPoint[];
  verdict: string;
  verdict_color: string;
  confidence_note: string;
}

export interface EmergencyPriority {
  zone_id: string;
  name: string;
  district: string;
  risk_score: number;
  severity: Severity;
  slope_state: SlopeState;
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

export interface RoadSegment {
  id: string;
  name: string;
  from_zone: string;
  to_zone: string;
  road_type: string;
  length_km: number;
  status: "OPEN" | "BLOCKED" | "DAMAGED" | "UNDER_REPAIR";
  blockage_reason: string | null;
  last_updated: string | null;
  reported_by: string | null;
  latitude: number;
  longitude: number;
}

export interface WeatherOverviewZone {
  zone_id: string;
  name: string;
  district: string;
  rainfall_24h: number;
  rainfall_72h: number;
  soil_moisture: number;
  risk_score: number;
  severity: Severity;
  risk_level: string;
  risk_color: string;
  message: string;
  escalated: boolean;
}

export interface WeatherOverview {
  forecasts: WeatherOverviewZone[];
  total: number;
  extreme_count: number;
  high_count: number;
  analyzed_at: string;
}

export interface EmergencyTask {
  id: string;
  zone_id: string;
  task_type: string;
  title: string;
  description: string;
  priority: string;
  status: "PENDING" | "IN_PROGRESS" | "COMPLETED";
  assigned_team: string | null;
  estimated_time: string | null;
  created_at: string | null;
  completed_at: string | null;
}

export interface SeveritySummary {
  summary: { LOW: number; MODERATE: number; HIGH: number; VERY_HIGH: number };
  zones: {
    zone_id: string; name: string; district: string;
    risk_score: number; severity: Severity; escalated: boolean;
    population: number; slope: number; elevation: number;
    road_proximity: number; rainfall_24h: number; soil_moisture: number;
  }[];
  total_zones: number;
  total_population: number;
  exposed_population: number;
  escalated_count: number;
  analyzed_at: string;
}

export interface RouteSegment {
  road_name: string;
  from_zone: string;
  to_zone: string;
  from_name: string;
  to_name: string;
  length_km: number;
  status: "OPEN" | "BLOCKED" | "DAMAGED" | "UNDER_REPAIR";
  blockage_reason: string | null;
  road_type: string;
  latitude: number;
  longitude: number;
  from_lat: number;
  from_lng: number;
  to_lat: number;
  to_lng: number;
}

export interface RouteCoord {
  lat: number;
  lng: number;
  zone_id: string;
  name: string;
}

export interface EvacuationRoute {
  route_available: boolean;
  algorithm: string;
  mode: string;
  source: string;
  target: string;
  source_name: string;
  target_name: string;
  distance_km: number;
  estimated_time_min: number;
  safety_score: number;
  risk_exposure: number;
  risk_level: "LOW" | "MODERATE" | "HIGH" | "UNREACHABLE";
  roads_used: RouteSegment[];
  roads_avoided: { road_name: string; status: string; reason: string | null }[];
  warnings: string[];
  path: string[];
  path_names: string[];
  route_coords?: RouteCoord[];
  geometry: { type: string; coordinates: number[][] };
  explanation: { why: string[]; tradeoffs: string[] };
  reason?: string;
  alternative_routes?: any[];
  reachable_zones?: string[];
}

export interface RouteNetwork {
  nodes: { id: string; name: string; lat: number; lng: number; population: number }[];
  edges: RouteSegment[];
  total_nodes: number;
  total_edges: number;
}

export interface ZoneListItem {
  id: string;
  name: string;
  district: string;
  lat: number;
  lng: number;
}

export interface SoilMoistureObservation {
  timestamp: string;
  soil_moisture: number;
  quality_flag: string;
}

export interface SoilMoistureResponse {
  state: string;
  label: string;
  freshness: string;
  observations: SoilMoistureObservation[];
}

export interface VisionObservation {
  observation_id?: number;
  id?: number;
  report_id: string | null;
  model_name: string;
  model_mode: string;
  landslide_detected: boolean;
  confidence: number;
  affected_pixel_ratio: number;
  observation_severity: string;
  bbox: number[];
  num_regions: number;
  geometry: { type: string; geometry: any; properties: any } | null;
  image_width: number | null;
  image_height: number | null;
  timestamp: string;
  warning: string | null;
  image_path?: string | null;
  zone_id?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  created_at?: string | null;
}

export interface VisionObservationRecord {
  id: number;
  report_id: string | null;
  model_name: string;
  model_mode: string;
  confidence: number;
  pixel_ratio: number;
  severity: string;
  landslide_detected: boolean;
  zone_id: string | null;
  latitude: number | null;
  longitude: number | null;
  image_path: string | null;
  warning: string | null;
  geometry: any;
  created_at: string | null;
}

export interface CorroborationResult {
  zone_id: string;
  zone_risk_score: number;
  zone_severity: string;
  observation_score: number;
  observation_severity: string;
  corroboration: string;
  explanation: string;
}

export interface VisionModelStatus {
  model: string;
  mode: string;
  checkpoint: string;
  status: string;
  trained_landslide: boolean;
  note: string;
}

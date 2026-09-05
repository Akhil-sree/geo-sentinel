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
  terrain: { slope: number; elevation: number; ruggedness: number; population: number } | null;
  drivers: Driver[];
  explanation: { factors: string[]; conclusion: string; recommended_action: string };
  model_versions: { rf: string; mamba: string; fusion: string };
  sim_time: string;
}

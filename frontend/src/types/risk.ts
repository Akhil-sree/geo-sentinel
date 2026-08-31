export type Severity = "LOW" | "MODERATE" | "HIGH" | "VERY_HIGH";

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
}

export interface RiskHistoryPoint {
  timestamp: string; risk_score: number; static: number;
  dynamic: number; severity: Severity; escalated: boolean;
}

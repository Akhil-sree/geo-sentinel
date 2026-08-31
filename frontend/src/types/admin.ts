export interface FreshnessEntry { source: string; state: string; note: string; }

export interface DataFreshnessResponse {
  mode: string; freshness: FreshnessEntry[];
  recent_ingestion_runs: { source: string; status: string; detail: string; at: string }[];
}

export interface ModelMetrics {
  positioning: string;
  rf: { version: string; validation: string; roc_auc: number; pr_auc: number; f1: number };
  baselines: Record<string, number>;
  early_warning_focus: string;
  thresholds_note: string;
}

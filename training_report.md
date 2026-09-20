# GEO-SENTINEL Training Report

Experiment `gs_v1` | seed 42 | status: prototype (EXPERIMENTAL)

## 1. Dataset Used
- `meghalaya_rf_training_features.csv` — sha256:545d224de7d9fb51
- `meghalaya_mamba_supervised_sequences_15f.csv` — sha256:16c6223ba42009b5
- `meghalaya_mamba_supervised_tensor_15f.npz` — sha256:22b511964a099939
- `meghalaya_high_confidence_events.csv` — sha256:324315f075749d51
- `event_manifest.csv` — sha256:b10b22fa7f96ef64
- `Landslide Reports.csv` — sha256:e5948a01e7f50128

## 2. Dataset Statistics
- RF: 54 rows (18 pos / pseudo-neg rest), 14 features
- Mamba: 666 seqs, 49 steps used (cutoff: strictly-before-event-day), 18 events
- Held-out pool: 20 lower-confidence COOLR events

## 3. Preprocessing
- Rainfall QC gates enforced (sentinel/negative/spike/duplicate rejects; see rainfall_qc JSON).
- Mamba StandardScaler fit on train folds only; tabular pipelines fit train-only.
- LULC codes kept as opaque categories (codebook missing).

## 4. Split Strategy
- Tabular: StratifiedGroupKFold-3 over event/spatial groups (10 km clustering).
- Mamba/fusion: GroupKFold-3 by event window — no shared-window leakage.
- Held-out: 20 lower-confidence events never used in training.

## 5. Leakage Checks
- Event-group CV everywhere; OOF-only fusion inputs; scaler train-only; pre-event-day cutoff for Mamba; all guards passed.

## 6. Model Configurations
- LogReg (scaled, balanced), RF (300 trees, balanced_subsample), HGB (200 iter, depth 3), XGB/LGBM (depth 3, balanced).
- Mamba: Linear15→16 + LayerNorm + Dropout0.2 + SelectiveSSMCell(d_state=8), AdamW 1e-3, early stopping, pos-weighted BCE.
- Fusion: balanced LogReg on [RF-OOF-proba, Mamba-OOF-proba].

## 7-9. Training / Validation / Independent Evaluation

| Model | Input | Split | ROC-AUC | PR-AUC | Recall | Precision | F1 | Brier | n |
|---|---|---|---|---|---|---|---|---|---|
| gs_logreg | logreg | event-grouped | 0.903 | 0.8465 | 0.8889 | 0.7333 | 0.7998 | 0.1291 | 54 |
| gs_rf | rf | event-grouped | 0.9444 | 0.9347 | 0.8333 | 0.8611 | 0.8364 | 0.0872 | 54 |
| gs_hgb | hgb | event-grouped | 0.5 | 0.3329 | 0.6667 | 0.2349 | 0.3467 | 0.25 | 54 |
| gs_xgb | xgb | event-grouped | 0.9474 | 0.9252 | 0.8333 | 0.8611 | 0.8364 | 0.0872 | 54 |
| gs_lgbm | lgbm | event-grouped | 0.8741 | 0.8648 | 0.7381 | 0.6793 | 0.6882 | 0.2178 | 54 |
| gs_mamba | mamba | event-grouped | 0.4468 | 0.0337 | 0.4444 | 0.0229 | 0.0433 | 0.2543 | 666 |
| gs_fusion | fusion | event-grouped | 0.9208 | 0.5088 | 0.8889 | 0.2319 | 0.3678 | 0.0848 | 666 |

- Held-out (terrain-core, 11/20 scored): recall@0.5 = 0.4545; 9 out of SRTM coverage.
- Small-n uncertainty dominates: see recall_ci95 in metrics JSONs; no model declared best from a single split.

## 10. Explainability
- See `models/gs_gis/explainability.md` (associative language only).

## 11. GIS Outputs
- Grid [120, 120] @ 0.01667 deg; 10800 valid cells; 130 watch+ points.

## 12. Limitations
- 18 positives; pseudo-negatives (not confirmed absence); SRTM lon 92–93 gap; rainfall spikes/sentinels; no SAR; SegFormer BLOCKED (void pixels, no masks); Mamba bg windows share event times (event-split mitigated); LULC semantics unknown; Jan-2020 .nc are schema samples, not a live feed.

## 13. Deployment Readiness
- Prototype: PARTIAL (end-to-end demo runs; segmentation + live warning missing)
- Research-grade: NO (n=18 positives; uncalibrated)
- Production: NO

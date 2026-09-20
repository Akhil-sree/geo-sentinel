# MODEL_TRAINING_REPORT.md — GEO-SENTINEL gs_v1 (independent TEST results)

All metrics below are **event-grouped cross-validation or blind held-out** —
never training performance. No result here is called "system accuracy".

## Dataset / split / config

- RF table `meghalaya_rf_training_features.csv` (sha256:545d224de7d9fb51): 54 rows,
  18 pos / 36 pseudo-bg; 14 features (schema in `models/random_forest/`).
- Mamba `...tensor_15f.npz` (sha256:22b511964a099939): 666 seqs (18 pos + 648 bg),
  73→49 steps after strictly-before-event-day cutoff, 15 features.
- Splits: tabular StratifiedGroupKFold-3 (10 km event/spatial groups);
  Mamba/fusion GroupKFold-3 by event window. Seed 42. Scalers fit train-only.
- Configs: `backened/configs/{datasets,training,models}.yaml`. Reproduce:
  `cd backened && python -m training.train_all --model all`.

## VALIDATION results (event-grouped CV)

| Model | ROC-AUC | PR-AUC | Recall | Precision | F1 | Brier | n |
|---|---|---|---|---|---|---|---|
| gs_logreg | 0.903 | 0.847 | 0.889 | 0.733 | 0.800 | 0.129 | 54 |
| gs_rf | 0.944 | 0.935 | 0.833 | 0.861 | 0.836 | 0.087 | 54 |
| gs_hgb | 0.500 | 0.333 | 0.667 | 0.235 | 0.347 | 0.250 | 54 |
| gs_xgb | 0.947 | 0.925 | 0.833 | 0.861 | 0.836 | 0.087 | 54 |
| gs_lgbm | 0.874 | 0.865 | 0.738 | 0.679 | 0.688 | 0.218 | 54 |
| gs_mamba | 0.522 | 0.047 | 0.667 | 0.027 | 0.052 | 0.273 | 666 |
| gs_fusion | 0.918 | 0.674 | 0.611 | 0.262 | 0.364 | 0.090 | 666 |

## TEST result (blind held-out, terrain-core RF)

20 lower-confidence COOLR events, never trained on: 11 scored (9 outside SRTM
coverage), **recall@0.5 = 0.45**. Package-CV optimism is explained by bg
sampling bias (bg ~9× farther from roads than events); the held-out number is
the honest generalization signal. Wilson CIs in per-model metrics JSONs.

## What was NOT trained

SegFormer — BLOCKED (49/49 optical patches constant-0, 11/11 QA constant-1,
0 masks). No masks fabricated; no segmentation metrics reported.

## Known limitations

18 positives; pseudo-absence (not confirmed absence); SRTM lon-92–93 gap;
rainfall spikes/sentinels; no SAR; LULC semantics unknown; Jan-2020 .nc are
schema samples; all probabilities uncalibrated; HGB instability at n=54.

## Integration

`GET /api/risk/gs_point?lat&lon`, `POST /api/risk/gs_tabular`,
`POST /api/risk/gs_sequence` (all DB-free, additive; existing routes untouched).
Temporal branch returns `temporal_risk: null` — gs Mamba is chance-level and
promotion-blocked, so it is not wired into live risk. GIS: 600×600 GeoTIFF +
watch+ GeoJSON points (`backened/models/gs_gis/`).

## Deployment readiness

Prototype PARTIAL · Research-grade NO · Production NO.

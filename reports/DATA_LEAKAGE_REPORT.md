# DATA_LEAKAGE_REPORT.md — GEO-SENTINEL gs_v1

Method: event/window-grouped splits everywhere + automated guards
(`backened/tests/test_geosentinel.py`: group-disjointness, scaler train-only,
sequence integrity, duplicate IDs). Status: **no known leakage; gates pass**.

## Checks performed

| # | Check | Result |
|---|---|---|
| 1 | Duplicate Point_IDs in RF table | none (54 unique) |
| 2 | Duplicate Mamba sequence_ids | none (666 unique) |
| 3 | Same event across train/val (tabular, StratifiedGroupKFold-3, 10 km groups) | disjoint ✓ (test) |
| 4 | Same event window across train/val (Mamba GroupKFold-3 by event) | disjoint ✓ (test) |
| 5 | Random row split of Mamba windows | FORBIDDEN by construction; worker has no row-split path |
| 6 | Scaler fit on full data | fitting happens on train folds only (worker `StandardScaler().fit(X[tri])`; tabular pipelines fit in-fold) ✓ (test) |
| 7 | Future rain in historical prediction | Mamba strictly-before-event-day cutoff (73→49 steps); gauge features use prior-day cutoff in `ner_v2_features` |
| 8 | Target-derived features | none (no trigger/category text, no post-event imagery as input) |
| 9 | Label↔feature circularity | RF terrain/OSM/soil independent of COOLR ✓ |
| 10 | OOF fusion inputs | both branches out-of-fold under event grouping ✓ |
| 11 | Same-scene imagery in multiple splits | N/A — no imagery used for training |
| 12 | Preprocessing fitted before split | none found (median-impute path in legacy script uses train rows only) |

## Residual risks (accepted, documented)

- Pseudo-background points may sit on unreported slides (label noise, not leakage).
- ERA5 spatial correlation across nearby cells mitigated by event grouping, not eliminated.
- Static SRTM underlies train and inference (legitimate for susceptibility; declared).
- Package-CV optimism from bg sampling bias (road distance) is a *sampling* issue,
  caught by the blind held-out check (recall 0.45) — not a split leak.

## SegFormer

No training occurred; leakage N/A. Gate refuses future runs until masks + valid pixels exist.

# ML_RELIABILITY_AUDIT.md — GEO-SENTINEL gs_v1 (re-verified 2026-09-18)

## Independent results (artifacts re-read + `--smoke` retrain today)

| Model | ROC | PR | F1 | Recall | Verdict |
|---|---|---|---|---|---|
| gs_rf (54: 18+/36bg) | 0.9444 (CV 0.929) | 0.9347 | 0.8364, CM [[34,2],[3,15]] | 0.833, CI95 [0.608,0.942] | Suspiciously strong; pseudo-negatives + point terrain likely separable |
| gs_logreg / xgb / lgbm / hgb | 0.903 / 0.9474 / 0.8741 / 0.50 | 0.847 / 0.925 / 0.865 / 0.333 | 0.800 / 0.836 / 0.688 / 0.347 | — | HGB collapse to chance at same n signals instability |
| gs_mamba (666, 18+) | 0.5221 (folds 0.449/0.520/0.597) | 0.0465 | 0.0524, CM [[208,440],[6,12]] | 0.667, CI95 [0.437,0.837] | Chance-level; Brier 0.27 worse than all-negative baseline 0.027 |
| gs_fusion artifact | 0.9176 | 0.6735 | 0.3636, CM [[594,54],[2,16]] | 0.889 | Carried by RF-OOF input; EXPERIMENTAL, uncalibrated, not served |
| terrain-core held-out | 0.5313 | — | 0.4037 | 0.4545 (5/11; 9/20 out-of-coverage) | Near-chance generalization — the honest counterweight to RF CV |

## Leakage audit — PASS with disclosed partials

- Scaler inside per-fold pipeline, fit on train only (`train_geosentinel.py:123-126`); Mamba per-fold scalers saved/loaded (`gs_mamba_worker.py:62-64`, `gs_inference.py:78`).
- Tabular `StratifiedGroupKFold-3` over 10 km event groups; Mamba/fusion `GroupKFold-3` by event window; fusion OOF-only inputs.
- 73→49 cutoff strictly-before-event-day confirmed (24 event-day hours removed, 666 kept, 0 dropped).
- Feature order: gs_v1 dict→schema-ordered vector both sides — order-safe by construction. Mamba order check is set-equality only (can't catch permutation; no mismatch evidenced).
- Residuals (all disclosed in-repo): spatial separation PARTIAL (district overlap), static features identical across a zone's yearly samples, bg singletons splittable, Mamba bg windows share event times. `leakage_check_passed` flags are self-asserted.
- SegFormer BLOCKED (no masks, constant patches) — no fake segmentation possible. Mamba excluded from live risk (`temporal_risk: null` on all gs outputs, verified live).

## Safe-to-display?

Demo + research: YES with the uncalibrated prototype labels the API already attaches. Production/early-warning: NO (n=18, CI widths dominate rankings, no calibration, no live feed).

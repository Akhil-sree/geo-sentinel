# MODEL COMPARISON — same held-out zones Z7/Z8 (n=6), native inputs each

Produced by `app/ml/benchmark_real.py` (2026-09-15). Static models retrained
on non-holdout zone-years; sequence models on real ERA5 sequences.

| Model | Inputs | Prec | Rec | F1 | ROC-AUC | PR-AUC | Brier |
|---|---|---|---|---|---|---|---|
| Heuristic | real 48h seq | 0.000 | 0.000 | 0.000 | 0.625 | **0.700** | 0.309 |
| LogReg | terrain6 | 0.000 | 0.000 | 0.000 | 0.500 | 0.333 | **0.228** |
| RF | terrain6 | 0.000 | 0.000 | 0.000 | 0.500 | 0.333 | 0.224 |
| GBM | terrain6 | 0.000 | 0.000 | 0.000 | 0.500 | 0.333 | 0.274 |
| Mamba v2026_03 | real 48h seq | 0.333 | **1.000** | **0.500** | 0.500 | 0.450 | 0.256 |
| Fusion expert 0.4/0.6 | static+mamba | 0.333 | 1.000 | 0.500 | 0.500 | 0.450 | 0.255 |

Reading (prioritizing PR-AUC/recall/F1 on imbalanced data): no model
separates n=6 — statics and heuristic predict all-negative (recall 0),
Mamba predicts all-positive (recall 1.0, precision 0.33). Best PR-AUC:
heuristic (0.70); best F1: Mamba/fusion (0.50); best Brier: LogReg (0.228).
No winner declared at this n; Mamba is the only model with nonzero recall,
which for early warning (FN-weighted) is the signal that justifies keeping
it EXPERIMENTAL rather than retiring it. Fusion adds nothing over Mamba
here (Brier 0.256→0.255) — expert weights stay as unvalidated config.

Contrast with GroupKFold CV on all 24 (events_v2): LogReg F1 0.526, GBM
0.500, RF 0.375 — the CV view and the holdout view disagree, which is
exactly what n=24 looks like. Both views are reported; neither is hidden.

## Modality ablation (occlusion on trained mamba_2026_03, n=6 holdout)

| Input | F1 | Brier |
|---|---|---|
| full sequence | 0.500 | 0.256 |
| rain channels zeroed | 0.500 | 0.252 |
| soil channels zeroed | 0.500 | 0.249 |
| rain+soil zeroed | **0.000** | 0.246 |

Rain and soil are redundant at this n (either alone sustains F1), but the
model genuinely uses the sequence channels: removing both collapses
prediction. Terrain-only static models (F1 0.0 here) contribute nothing on
this holdout — another reason fusion stays unvalidated config.

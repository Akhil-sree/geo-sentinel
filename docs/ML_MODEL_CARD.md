# ML MODEL CARD (events_v2, spatial GroupKFold-3 by district, n=24)

| Model | Acc | Prec | Rec | F1 | F1-m | F1-w | ROC-AUC | PR-AUC | Brier | ECE | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LogReg | — | 0.556 | 0.500 | 0.526 | — | — | 0.586 | 0.519 | 0.273→0.247* | — | DEMO |
| RF event | — | 0.500 | 0.300 | 0.375 | — | — | 0.629 | 0.540 | 0.236 | — | DEMO |
| GBM event | — | 0.667 | 0.400 | 0.500 | — | — | 0.521 | 0.509 | 0.296 | — | DEMO |
| Stacking (OOF) | — | 0.000 | 0.000 | 0.000 | — | — | 0.393 | 0.426 | 0.258 | — | REJECTED (evidence) |
| RF prod (rf_2026_01) | 0.50 | 0.167m | 0.333m | 0.222m | 0.222 | — | — | — | — | — | DEMO (in path, labeled) |
| Mamba mamba_2026_02 | 0.94† | — | — | 0.938† | — | — | — | — | 0.101† | — | EXPERIMENTAL |
| Mamba mamba_2026_03 | 0.333‡ | — | 1.000‡ | 0.500‡ | — | 0.500‡ | 0.450‡ | 0.256‡ | — | — | EXPERIMENTAL |

m = macro. * Platt-sigmoid kept (Brier improved). † SIMULATED storm-sequence
task (next-24h >80mm from past-48h, zone-holdout) — pipeline validation, NOT
operational skill. ‡ REAL ERA5 sequences (seq_real_v1, spatial holdout
Z7/Z8, n=6): the only model with nonzero recall; statics/heuristic score
F1 0.0 there — see `MODEL_COMPARISON.md`. Production risk uses uncalibrated
scores (`probability_status` exposed; reliability bins at
`/model/reliability`).

Intended use: decision-support advisory only. Out of scope: evacuation
orders, house-level claims. Limitations: n=24, static features, weak signal
(permutation importance ≈ 0 even in-sample). Promotion gate: n≥50, F1≥0.60,
recall≥0.60, Brier≤0.25, leakage+spatial-validation pass — all enforced by
`registry.evaluate_promotion` (currently BLOCKED for everything).

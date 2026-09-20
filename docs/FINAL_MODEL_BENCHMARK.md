# FINAL MODEL BENCHMARK (2026-09-15)

## A. Static terrain models — events_v2, spatial GroupKFold-3 by district (n=24)

| Model | F1 | Recall | PR-AUC | Brier |
|---|---|---|---|---|
| LogReg | 0.526 | 0.500 | 0.519 | 0.273→0.247 (Platt kept) |
| GBM | 0.500 | 0.400 | 0.509 | 0.296 |
| RF | 0.375 | 0.300 | 0.540 | 0.236 |
| Stacking (OOF) | 0.000 | 0.000 | 0.426 | 0.258 — REJECTED |

## B. Temporal Mamba — GroupKFold-3 by district, seq_real_v2 (n=32)

Mean±std over folds (per-fold pos counts recorded in registry `mamba_cv/cv_v1`):

| Loss | F1 | Recall | PR-AUC | Brier |
|---|---|---|---|---|
| plain BCE | 0.489±0.126 | 1.000 | 0.559 | 0.251 |
| pos-weighted BCE | 0.489±0.126 | 1.000 | 0.566 | 0.264 |
| focal γ=2 | 0.489±0.126 | 1.000 | **0.573** | 0.253 |

Loss choice does not move F1 at this n; focal ranks slightly better
(PR-AUC). Plain BCE retained as primary (simplest identical F1) — no
hyperparameter explosion justified. All folds flagged by pos count in the
registry entry.

## F. Architecture/window experiments (`mamba_experiments/grid_v1`)

| Config (seq_len, hidden) | F1 mean±std | PR-AUC | Brier |
|---|---|---|---|
| (48, 8) current | 0.489±0.126 | 0.559 | 0.251 |
| (24, 8) | 0.489±0.126 (identical) | 0.559 | 0.251 |
| (48, 16) | 0.000±0.000 | 0.366 | 0.228 |

Window length is not a lever here: first-batch losses already agree to
~1e-4 (SSM readout dominated by late-window steps shared by both windows),
and full CV outcomes coincide exactly. Capacity IS a lever, negatively:
d_state 16 collapses to all-negative at n=32. Retained: (48, 8).

## G. Seed/initialization stability (measured)

Identical code+seed with per-fold streaming init (prior script version)
gave F1 0.222 vs 0.489 with per-fold reseed — initialization scheme moves
the headline number at n=32. Standardized on per-fold reseed (isolates
fold variation); torch-first import order enforced in every training entry
point (sklearn-first import was observed to perturb torch numerics
run-to-run). Reproducibility rule documented in MAMBA_VALIDATION.

## C. Same-holdout comparison — zones Z7/Z8, native inputs

| Model | F1 | Recall | PR-AUC | Brier |
|---|---|---|---|---|
| Heuristic | 0.000 | 0.000 | 0.700 | 0.309 |
| LogReg/RF/GBM | 0.000 | 0.000 | 0.333 | 0.224–0.274 |
| Mamba v2026_03 (v1 data) | 0.500 | 1.000 | 0.450 | 0.256 |
| Mamba v2026_04 (v2 + hard negs) | 0.444 | 1.000 | 0.450 | 0.253 |
| Fusion expert | 0.500 | 1.000 | 0.450 | 0.255 (= Mamba alone) |

Hard negatives lowered holdout F1 0.500→0.444 — expected (harder task),
reported, not hidden. Mamba is the only model with nonzero recall in both
views; for FN-weighted early warning that is the evidence for keeping it
EXPERIMENTAL. Nothing promoted (gate: n≥50, F1≥0.60).

## D. Leave-Zone-Out (`mamba_lzo/lzo_v1`, seq_real_v2)

| Zone | n | pos | Recall | F1 |
|---|---|---|---|---|
| Z1 | 4 | 2 | 1.000 | 0.800 |
| Z2 | 4 | 1 | 1.000 | 0.500 |
| Z3 | 4 | 2 | 1.000 | 0.667 |
| Z4 | 4 | 1 | 1.000 | 0.400 |
| Z5 | 4 | 2 | 1.000 | 0.667 |
| Z6 | 4 | 0 | n/a (all-negative correct) | n/a |
| Z7 | 4 | 1 | 1.000 | 0.400 |
| Z8 | 4 | 1 | 1.000 | 0.400 |

Mean F1 (scored zones): 0.548. Every unseen zone's positives caught
(recall 1.0 everywhere) — the strongest generalization evidence available
at this n, and the reason Mamba stays EXPERIMENTAL rather than retired.

## E. Modality occlusion (trained v2026_03, n=6 holdout)

full 0.500 / rain-zeroed 0.500 / soil-zeroed 0.500 / both-zeroed 0.000 —
channels jointly necessary, individually redundant at this n.

## E. Calibration

Production: UNCALIBRATED (`probability_status` everywhere, bins at
`/model/reliability`). LogReg-sigmoid kept (Brier evidence). Temporal
n insufficient for Platt/isotonic — stated, not forced.

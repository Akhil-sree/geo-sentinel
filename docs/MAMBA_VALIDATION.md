# MAMBA VALIDATION (preserved, trained, not operational)

Implementation: selective-SSM cell (`app/ml/mamba_model.py`, Gu & Dao 2023
pattern) over 48×7 environmental sequences (rain norms, slope, soil, SAR
neutral) — `temporal_backend` always reported.

Training (SIMULATED task): `app/ml/train_mamba.py` → `mamba_2026_02`
(next-24h exceedance on storm curves): val F1 0.938, Brier 0.101 —
machinery learns a deterministic curve; says NOTHING about real
landslides. EXPERIMENTAL, gate BLOCKED.

Training (REAL seq_real_v1): `app/ml/train_mamba_real.py` → `mamba_2026_03`,
holdout Z7/Z8: F1 0.500, recall 1.000, PR-AUC 0.450, Brier 0.256.
EXPERIMENTAL, gate BLOCKED.

Training (REAL + hard negatives, seq_real_v2): → `mamba_2026_04`: F1 0.444,
recall 1.000, CM [[1,5],[0,2]] — harder task, honestly lower F1.
EXPERIMENTAL, gate BLOCKED (n=32).

CV (REAL seq_real_v2, GroupKFold-3 by district + inner holdout):
`app/ml/cv_mamba.py` — plain/weighted/focal all F1 0.489±0.126, recall
1.000; focal PR-AUC 0.573 best. Loss choice does not move F1 at this n;
plain BCE retained. Per-fold counts in registry `mamba_cv/cv_v1`.
Full tables: `FINAL_MODEL_BENCHMARK.md`.

Operational rule (unchanged): `get_temporal_model()` returns the trained
net ONLY with `MAMBA_LIVE=true` + existing weights + PROMOTED status;
otherwise the labeled heuristic. `/model/status` exposes which.

Environment note: torch 2.11 CPU present but its DLLs intermittently fail
to load after sklearn in the same process (WinError 1114) — `mamba_model`
catches OSError → honest heuristic fallback. Train in a fresh process.

To operationalize: observed sequences (rain+soil histories per event) +
registry PROMOTED + evidence here. Until then: TRAINING_REQUIRED/DEMO.

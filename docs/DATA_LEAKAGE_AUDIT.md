# DATA LEAKAGE AUDIT (2026-09-15, events_v2)

Method: code inspection + `scripts/validate_dataset.py` (gates 1–6) + this
checklist. Dataset: 8 zones × 3 years = 24 samples, static terrain features,
district-grouped spatial CV.

| # | Check | Result | Evidence | Mitigation |
|---|---|---|---|---|
| 1 | Same event in train and validation | PASS | District GroupKFold; seed events unique per zone-year (gate 4) | groups=district, no event split across folds |
| 2 | Same zone across temporal windows | ACKNOWLEDGED | Same zone appears in 3 yearly samples with identical static X | District grouping keeps a zone's years in one fold; documented that static features cannot separate years (see SOURCES.md) |
| 3 | Future rainfall as feature | PASS | Static ML uses terrain only; rainfall enters only the live fusion path, never training | `dataset.FEATURES` has no rainfall columns (gate 4c) |
| 4 | Post-event soil moisture in training | PASS | Same as 3 — no soil columns in training | gate 4c |
| 5 | Future satellite observations | PASS | SAR excluded from features (mock-leakage) and from production risk (neutral 0.15) | `sim.py` quarantine + provenance |
| 6 | Labels as features | PASS | Schema = 6 terrain columns; guard rejects label-like names | gate 4c |
| 7 | Preprocessing fitted on full data | PASS | No fitted preprocessing: features are raw seed values, elevation scaled by fixed /2000 divisor (not data-fitted) | fixed divisor, no scaler object |
| 8 | Normalization leakage | PASS | Same — no mean/std computed from data | by construction |
| 9 | Duplicate event IDs / coords / dates | PASS | Gates 4/4b reject same-zone same-date dupes and shared coordinates | hard errors |
| 10 | Temporal leakage (future→past) | PASS | Labels use only events within the sample year; no rolling future windows | label definition in metadata |
| 11 | Spatial leakage (nearby-event) | PARTIAL | District blocking is coarse; adjacent districts can share borders | acknowledged; block size is the honest limit at n=24 — finer blocks need denser inventory (roadmap) |
| 12 | CSV↔DB drift | PASS | Gate 4d compares artifact row-for-row | `data/process_events.py` regenerates |
| 13 | Mock data in production path | PASS | Ingestion tags source/quality; provider_states surfaces is_live; sim neutralizes SAR | tests: stale-not-mock, quarantine |
| 14 | Mamba random-init predictions | PASS | `get_temporal_model` returns heuristic unless trained checkpoint + `MAMBA_LIVE` | `temporal_backend` exposed; training pipeline (Phase 5) registers before any promotion |

Overall: no blocking leakage. Known residual: coarse spatial blocking (#11)
and static-feature year ambiguity (#2) — both inherent to n=24, both
documented, both gated by the registry promotion rule (n≥50).

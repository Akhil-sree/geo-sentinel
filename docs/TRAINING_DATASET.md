# TRAINING DATASET ner_v1

- Version: `ner_v1` (immutable CSV + metadata + checksum
  `sha256:d91ef7028339fb28`;
  ledger row in `dataset_versions`). Reruns bump the version, never overwrite
  (explicit `--force` rebuilds update the ledger row openly as
  `DRAFT (rebuilt --force)`).
- Samples: n=30 (10 RECORDED_LANDSLIDE demo-seed exact-date events + 20
  matched NO_RECORDED_LANDSLIDE controls: same site, same month-day,
  non-event year, ±30d exclusion).
- Splits: train 15 / val 3 / test 12. Test = most-recent-positive-year (2024)
  positives + their linked controls; val = West Jaintia Hills (no test
  positives); train = rest. Temporal direction verified (train 2022–23 < 2024).
- Features (36, `nerfeat_v1`): rain windows 1h–30d + maxima + intensity +
  trend + antecedent (REAL archive); soil current/1d/3d/7d (ALL MISSING —
  archive serves nulls, SMAP AUTH_REQUIRED); terrain 5x5 stats (REAL SRTM,
  same method both classes); SAR metadata (REAL, non-numeric → excluded from
  model inputs); exposure road/village/infra distances (STATIC registries).
  GSI density/distance EXCLUDED from model inputs (future-inventory leakage).
- Missingness: every gap coded (NOT_AVAILABLE/NOT_ACQUIRED/AUTH_REQUIRED);
  group-median imputation for observed columns, recorded per cell.
- Lineage: `ner_inventory` (871 NER: 10 temporal + 861 GSI spatial) →
  `training_samples` (provenance + missingness JSON) → CSV.
- Legacy preserved: `seq_real_v2` (n=32) untouched — DEMO/BASELINE dataset.
- Comparison: demo n=24–32 zone/sequence scope vs ner_v1 n=30 event-anchored
  with real rainfall/terrain/SAR-metadata provenance per sample; both small,
  both gate-BLOCKED — ner_v1 adds traceability, not scale.

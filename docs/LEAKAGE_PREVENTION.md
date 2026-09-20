# LEAKAGE PREVENTION

Binding gates (`scripts/run_leakage_checks.py --version ner_v1`; suite
`tests/test_training_leakage.py`):
- No future rainfall/soil: raw caches audited hour-by-hour against event end;
  features clip to ≤T.
- No future satellite: metadata-only (pre/post acquisition dates + same-orbit
  flag); no backscatter/imagery keys anywhere (asserted in tests).
- No future inventory: GSI density/distance EXCLUDED from model inputs
  (present-day catalog would leak post-event occurrences).
- No measurement bias: identical DEM method (SRTM 5x5) and rain method for
  both classes — caught and fixed during build (seed-profile vs SRTM scale
  split, imputation-constant controls).
- Temporal direction: all train positives (2022–23) predate test positives
  (2024). Control windows never overlap event windows (different years).
- Split integrity: unique sample_ids, class balance every split, controls
  follow linked events, canonical dedup.
- Disclosed PARTIAL (not hidden): district overlap across splits (fixed sites
  repeat across years at n=30 — same convention as DATA_LEAKAGE_AUDIT #11).
- No label-as-feature; no silent zeros (all-missing columns stay empty).

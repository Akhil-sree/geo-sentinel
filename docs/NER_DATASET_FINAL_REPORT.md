# NER DATASET FINAL REPORT (reproducible NER-scale pipeline, v1 honest outcome)

## WHAT IS REAL
- GSI Meghalaya inventory via CC0 mirror: 865 records, 861 NER (SPATIAL).
- Open-Meteo archive rainfall: 30/30 event+control 31d windows (observed blend).
- SRTM 30m terrain: 30/30 5x5 windows, identical method both classes.
- Sentinel-1 metadata: ASF discovery 10/10 events (pre/post scenes, orbits).
- OSM roads: Overpass per-zone highway counts 8/8 zones.
- Pipeline code, dedup, provenance, leakage gates, tests (17 new).

## WHAT IS MODELED
- Soil moisture fallback concept (ERA5-Land) — in ner_v1: entirely missing
  (archive serves nulls), coded NOT_AVAILABLE, never zero-filled.

## WHAT IS MOCK
- Demo seed events (10 EXACT_DATE, synthetic) — the only temporal positives
  available in this environment; tagged `demo` in every artifact.

## WHAT IS AUTH_REQUIRED
- SMAP L3 (Earthdata login), Sentinel-1 imagery (Copernicus creds).

## WHAT IS STALE / UNAVAILABLE
- NASA COOLR bulk: FAILED (egress 404; retry with full egress or --manual).
- NRSC Atlas: MANUAL_DOWNLOAD_REQUIRED (no bulk endpoint exists; count = 0, never 80k).
- GSI Bhukosh direct: registration-gated (mirror used instead).

## WHAT IS SCIENTIFICALLY VALIDATED
- Pipeline mechanics: pre-event clipping, dedup, provenance, split integrity,
  temporal direction, measurement parity — all gated PASS (PARTIAL disclosed).

## WHAT REMAINS EXPERIMENTAL
- Everything predictive: ner_v1 n=30 is a traceability foundation, not scale.
  All ner models EXPERIMENTAL + gate-BLOCKED. No operational claim.

## Coverage / counts
- Inventory: 871 NER (10 temporal + 861 spatial), 0 rejected, 4 non-NER excluded.
- Training: 10+/20−, splits 15/3/12, 5 district groups, holdout 2024.
- Features: 36 schema (16 rain REAL, 8 terrain REAL, 3 SAR metadata,
  3 exposure STATIC, 5 soil missing, spatial-context excluded).
- Missingness: soil 100%, sar_same_orbit 100% (documented causes).

## Reproduce
`ingest_gsi → build_inventory → build_controls → fetch_rainfall →
ingest_dem → ingest_sentinel1 → ingest_osm → build_features →
build_training_dataset --region NER --version ner_v1 →
run_leakage_checks → train_models → evaluate_models → final_dataset_audit`
(COOLR/NRSC/SMAP contribute when their access conditions are met.)

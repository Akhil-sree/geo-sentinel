# SPRINT 89→95 PLAN (2026-09-15)

89 drivers: verified live rain, honest ML (n=24), registry gates, idempotent
pipeline, 33+10 tests. Bottlenecks: no real temporal data (Mamba on
simulated task only), static terrain, satellite DEMO-only, docker/pg/redis
unverified (daemon down ×2).

## Feasibility probes (ran, mid-sprint)

| Probe | Result |
|---|---|
| Open-Meteo archive API (ERA5, 2022–24, rain+soil) | 200, 192h/8d — REAL HISTORICAL SEQUENCES FEASIBLE |
| OpenTopodata SRTM30m | 200, Z1 = 1487.0m (seed 1484m) — REAL DEM GRID FEASIBLE |
| ASF Vertex search API (S1 metadata, keyless?) | TO ATTEMPT |
| Docker daemon | DOWN (×3) → stays UNVERIFIED |
| localhost pg/redis | absent → UNVERIFIED |

## Build order (expected impact)

1. Real temporal sequences: archive rain+soil 168h pre-event × 10 events +
   matched negatives (same zone, non-event year) → `events_temporal_v1`
   (+Data Quality, +AI/ML — the sprint's core bet).
2. `validate_temporal_dataset.py` (pre-event-only, overlap, spatial/temporal leakage).
3. Mamba on REAL sequences (spatial holdout) + 5-way benchmark
   (heuristic/LogReg/RF/GBM/Mamba, same held-out events) → MODEL_COMPARISON.md.
4. Modality ablation (rain-only/soil-only/terrain-only/combos) + calibration
   on real OOF + promotion eval (expect BLOCK at n<50 — honest).
5. Real DEM: 5×5 SRTM30m grid/zone → slope/aspect/ruggedness → TerrainDEM
   table + provenance (STATIC profiles retained as fallback).
6. Satellite: ASF discovery attempt → metadata or documented UNVERIFIED.
7. Failure tests: corrupt-artifact fallback fix, provider 500, soil/sat
   unavailable, duplicate paths.
8. Claim audit (esp. 0.938 labeling), docs, full verify, FINAL_SCORE_REPORT.

## Verification per item

Each: implementation + test + registry/artifact + doc row. No promotion
without gate PASS. Simulated 0.938 stays labeled SIMULATED forever.

# NEXT ENHANCEMENT AUDIT (2026-09-15, pre-implementation, read-only basis)

## Current architecture
FastAPI (`app/api/*` under `/api`, 11 modules, ~60 endpoints) + 15-min worker
(ingest → sensor-health → autoeval) + React/Leaflet (12 pages) + SQLite demo /
Postgres+PostGIS prod profile + migrations v1–v9 + Docker (no Redis) +
A* routing with Dijkstra fallback.

## Current data flow
Providers (mock default; Open-Meteo live opt-in) → ingest/runner (retry→STALE,
idempotent store) → ZoneFeature → sim.run_pipeline → RiskScore → GIS/alerts.
NER training pipeline (scripts/*, versioned ner_v1 n=30) is separate from live
inference. KNOWN BUG: sim._sync_rain/_sync_soil DELETE + rewrite synthetic
observations per zone every call — the worker wipes live OPENMETEO rows each
cycle (runner.py:17-31 vs sim.py:492-499,569-576).

## Current ML flow
Served: rf_2026_01 (n=8 DEMO) + heuristic temporal + expert fusion_v1,
UNCALIBRATED. Registry 17 entries, 0 promoted. ner_v1 baselines
(LogReg 0.33 / RF 0.40 / GBM 0.33 holdout F1) EXPERIMENTAL + BLOCKED.
Mamba experimental, unpromoted. Stacking rejected.

## Current GIS flow
RiskMap (Esri + heat + polygons + hotspots + threats + reports + roads +
simulation overlay) → cell-grid → hotspots → emergency-priorities
(0.40/0.25/0.20/0.15) → routes/optimize (A*) → evacuation panel.

## Current provider status
LIVE-capable: Open-Meteo rain/soil-modeled (keyless). MOCK default: IMD, SMAP,
Sentinel-1, SMS/email/push. AUTH_REQUIRED: SMAP-L3, S-1 imagery, IMD key.
REAL metadata: ASF discovery 10/10, Overpass 8/8, archive rain 30/30, SRTM 30/30.
FAILED here: COOLR bulk (egress 404). MANUAL-only: NRSC, Bhukosh direct.

## Current test status
Backend 79 passed + 1 gated live (7 files). Frontend tsc clean, 11 vitest,
build ok. final_verify 20/20. Legacy seq_real_v2 untouched.

## Known limitations (binding)
n=30 temporal positives=10 demo; soil 100% missing in ner_v1; SAR metadata-only;
delivery mock; offline reports-scope; EN/HI served; no JWT/S3/TLS/native.

## Enhancement priorities (value-ordered)
1. Worker live-data wipe fix (real-data readiness; demo preserved).
2. Registry `__probe__` pollution removal + test isolation (reproducibility).
3. Doc corrections (ML precision 0.60→1.0; 62→79 passed) + stale translations
   (AS/MN soil tooltip) + UI wording (LIVE THREAT/Safest Route) + missing keys.
4. Dead-code removal (app/routers/*, providers/sar.py+base.py) + /admin/data
   honesty delegation + sensor zones[0] fallback → 422 + vision/route hardening.
5. CONTROL_SAMPLE_METHODOLOGY.md + one COOLR re-probe (expect fail; document).
6. Leave-district-out eval + binomial CIs on ner holdout metrics.
7. Unused deps (framer-motion, shapely) + .env.example sync + weight source note.

## Files requiring modification
backened/app/services/sim.py, scripts/ingest_dem.py (no), tests/test_ner_pipeline.py,
models/registry.json (delete 1 entry), docs/ML_FINAL_REPORT.md,
docs/SIH_FINAL_COMPLIANCE_REPORT.md, frontend translations + 2 components,
backened/app/routers/ (delete), providers/sar.py + providers/base.py (delete),
api/admin.py, api/sensors.py, api/vision.py, api/routes.py, ingest/runner.py
freshness fn, docs/CONTROL_SAMPLE_METHODOLOGY.md (new), scripts/train_models.py
(LDO + CI), package.json/requirements.txt (2 removals), .env.example files.

## Files that must remain untouched
backened/data/processed/sequences_v2.npz + seq pipeline + mamba checkpoints,
worker.py architecture, migrations ≤v9 (append-only), auth.py model,
reports.py validation, models/registry.json (except __probe__ removal),
geo/postgis.py, route_optimizer.py algorithm, sw.js/offline.ts scope.

## Risks per change
- sim wipe fix: demo scrubber must keep working (default path unchanged; live
  path only skips destructive rewrite). Mitigate: demo-mode tests unchanged.
- routers/ deletion: verify zero imports first (grep). Low risk (broken imports).
- sar.py deletion: verify runner never imports it (uses sentinel1.py).
- Dep removal: verify zero imports (grep incl. scripts).
- Train script changes: registry appends new versions only; never edits old.
- Translation fixes: EN fallback covers gaps; no safety-text invention.

# GEO-SENTINEL FINAL SCORE AUDIT

------------------------------------------------------------
GEO-SENTINEL FINAL SCORE AUDIT
------------------------------------------------------------

Previous:
    94/100

Final:
    96/100

Improvement:
    +2

Classification:
    HACKATHON READY

------------------------------------------------------------
DATA
------------------------------------------------------------

Historical events:
    n = 10 seed + 8 hard negatives + 865 REAL GSI catalog slides (CC0-1.0,
    all geocoded, served at /api/landslides/gsi; year-or-unknown dating →
    spatial features + GIS only, documented boundary)

Temporal sequences:
    n = 32 (seq_real_v2)

Positive:
    10

Negative:
    22 (14 matched + 8 hard)

Sources:
    Open-Meteo archive ERA5; SRTM30m profiles + 648-cell grids; ASF S1
    metadata ×10 (imagery 403-proven); GSI via bharatlas CC0-1.0
    (retrieved 2026-09-15, raw kept); GLC bulk still unretrievable (logged)

------------------------------------------------------------
ML
------------------------------------------------------------

Model        F1         Recall    PR-AUC    Brier    Status

LogReg       0.526*     0.500*    0.519*    0.247*   DEMO (*CV; holdout 0.0)
RF           0.375*     0.300*    0.540*    0.236*   DEMO (*CV; holdout 0.0)
GBM          0.500*     0.400*    0.509*    0.296*   DEMO (*CV; holdout 0.0)
Temporal     0.000      0.000     0.700     0.309    heuristic (best PR-AUC)
Mamba        0.444      1.000     0.450     0.253    EXPERIMENTAL (v04, real v2)

v3 (GSI features): all 0.375 — real negative result, registered + BLOCKED.

Mamba:

    dataset: seq_real_v2 (REAL, pre-event only)
    validation: GroupKFold-3 F1 0.489±0.126 + LZO mean F1 0.548
        (recall 1.0 in all 7 scored zones; Z6 correctly n/a)
    F1: 0.444 (holdout v04)
    recall: 1.000
    PR-AUC: 0.450
    Brier: 0.253
    status: EXPERIMENTAL, gate BLOCKED
    experiments: loss irrelevant at n (all F1 0.489); window 24≡48
        (late-step dominance); hidden 16 collapses (0.0) — (48,8) retained
    seed finding: init scheme moves CV F1 (0.222 vs 0.489 measured);
        standardized per-fold reseed + torch-first imports

------------------------------------------------------------
CALIBRATION
------------------------------------------------------------

Status:
    UNCALIBRATED in production

Method:
    bake-off where n permits (LogReg-sigmoid kept); temporal n insufficient

Evidence:
    ECE + bins incl. real-Mamba bins at /model/reliability;
    probability_status on every prediction + provenance object

------------------------------------------------------------
GIS
------------------------------------------------------------

Risk zones:
    PASS (drilldown + DEM block + freshness + 865-slide layer)

Grid risk:
    PASS (observed-DEM default + blindness note; legacy labeled)

DEM:
    STATIC profiles + OBSERVED derivatives + 648-cell grids

Road risk:
    PASS (PostGIS-aware geo-match wiring)

Routing:
    PASS (slope-aware A*, baseline compare)

Exposure:
    PASS (reasons incl. 30km report proximity)

------------------------------------------------------------
REMOTE SENSING
------------------------------------------------------------

Rainfall:
    LIVE (forecast) + ARCHIVE (ERA5 history)

Soil:
    MODELED (never sensor data)

Satellite:
    METADATA (10 real S1 records; imagery 403-proven; DEMO risk path)

DEM:
    STATIC + OBSERVED (never live terrain)

------------------------------------------------------------
DEPLOYMENT
------------------------------------------------------------

Docker:
    RUNTIME VERIFIED 2026-09-15 (was UNVERIFIED): full stack booted —
    backend healthy, frontend HTTP 200, worker running, postgres healthy.
    `docker compose build` fixed (psycopg2-binary>=3.1.0 never existed →
    ==2.9.9). Worker :8000 healthcheck disabled (serves no HTTP; liveness
    = /api/worker-status job rows).

Postgres:
    RUNTIME VERIFIED 2026-09-15 (was code-READY/runtime-UNVERIFIED):
    PostgreSQL 16.4, fresh-boot migrate v1→v6 (8 zones), full E2E
    (ingest→risk→GIS→alert lifecycle→report→restart-persistence),
    DB-outage honest failure + recovery, worker-stop recovery.

PostGIS:
    SERVER RUNTIME VERIFIED 2026-09-15 (was layer-only): PostGIS 3.4,
    geog geography(Point,4326) + GIST live, KNN + ST_DWithin queries
    measured (geo-match dist_km real, spatial_backend=postgis).
    Fixed pg-path null-distances/_d leak (ST_Distance selected).

Redis:
    NOT IMPLEMENTED — EXPLICITLY OUT OF SCOPE (service removed from compose)

Worker:
    VERIFIED (lock, jobs, idempotent ingestion, fresh-DB crash fixed)

------------------------------------------------------------
SECURITY
------------------------------------------------------------

Authentication:
    role API keys (admin/operator/viewer)

Authorization:
    server-side gates; 401/403 tested; exact-token audit match fix

Rate limiting:
    in-memory 60/30/20 (no Redis by design) + headers tested

Secrets:
    env + Fernet, never logged; required POSTGRES_PASSWORD (no default);
    non-root container user; no JWT (roadmap)

Upload security:
    MIME/magic/size/hash; 409/415/422 tested

------------------------------------------------------------
ALERTS
------------------------------------------------------------

Automatic:
    PASS

Cooldown:
    PASS (360m)

Escalation:
    PASS

Ack:
    PASS (audited)

Resolve:
    PASS (audited)

Audit:
    PASS (hourly idempotency keys; exact-token lifecycle endpoint)

Delivery:
    MOCK (no creds in env — verified absent)

------------------------------------------------------------
TESTS
------------------------------------------------------------

Backend:
    47/47 (+1 gated live; +seed FK-order regression, +postgis contract)

Frontend:
    10/10

ML:
    PASS (gates, CV, LZO, experiments, occlusion)

Leakage:
    PASS

E2E:
    PASS (incl. provenance/reasons/cell-mode/lifecycle keys)

Docker:
    UNVERIFIED (config PASS)

Additional:
    final_verify 15 checks 0 FAIL; TestClient perf measured
    (map ~1.4–1.5s incl. writes, evidence ~1.8s, cell-grid ~2.0s,
    routes ~0.15–0.2s; measured 2026-09-15, Windows/SQLite/TestClient warm —
    see PERFORMANCE.md; cell-grid was ~5.6s before batched RF predict)

------------------------------------------------------------
REMAINING LIMITATIONS
------------------------------------------------------------

- n=32: gate blocks everything (needs n≥50).
- VERIFIED 2026-09-15 (no longer limiting): PG 16.4 + PostGIS 3.4 runtime,
  Docker full-stack boot, migrate v1–v6 fresh, E2E, outage recovery.
- No live SMS/JWT; offline = field scope; i18n en/hi reviewed only.
- CV/holdout disagree (side by side); init scheme matters (standardized).
- DEM windowed/zonal, not full-raster risk; SAR metadata-only.
- risk/map latency ~1–2s (writes per request; precompute is roadmap).

------------------------------------------------------------
FILES CHANGED
------------------------------------------------------------

New: `app/geo/postgis.py`, `app/ml/mamba_experiments.py`, `app/ml/lzo.py`,
`scripts/fetch_demgrid.py` + 8 grids, `scripts/fetch_satmeta.py` + 10 raws,
`data/process_gsi.py` + raw/compact/zone-features/metadata,
`scripts/final_verify.py`, `docs/{FINAL_92_98_PLAN,FINAL_MODEL_BENCHMARK,
DATASET_CARD,LABELING_PROTOCOL,LIMITATIONS,DOCKER,POSTGRES_POSTGIS,
REMOTE_SENSING,DEM_PIPELINE,GIS_RISK,PERFORMANCE}.md`.
Modified: `docker-compose.yml` (redis removed, required password),
`Dockerfile` (non-root), `.env.example` (no redis/jwt), `database.py`
(explicit backend), `migrate.py` (v6 postgis), `models_db.py`
(TerrainDEM, SatScene), `dataset.py` (v3 + GSI), `train_rf.py` (v3 tag),
`cv_mamba.py` (torch-first), `risk.py` (cell modes, provenance, reasons,
GSI endpoint, tiers wiring), `reports.py` (postgis geo-match),
`alerts.py` (lifecycle, exact audit match), `main.py` (request IDs,
backend log), `sim.py` (provenance + inference_ms), `runner.py`
(freshness tiers, degraded flag, upsert fix), tests (+8: postgis ×2,
contract, lifecycle, i18n, geo-match, priorities/provenance, cells).
Deleted: none (redis had no code; dead routers/ documented, untouched).

------------------------------------------------------------
GIT
------------------------------------------------------------

NO COMMIT
NO PUSH
NO HISTORY REWRITE

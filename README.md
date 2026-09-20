# GEO-SENTINEL — AI Landslide Early Warning (NER India)

Zone-level landslide risk advisory + GIS decision support for Meghalaya (8 demo zones).
Stack: FastAPI + SQLite (demo) / Postgres-ready, React + Leaflet, RF + heuristic-temporal fusion.

## What is LIVE vs SIMULATED (read this first)

| Area | Status |
|---|---|
| Rainfall | **SIMULATED** by default (synthetic monsoon, persisted + deterministic). **LIVE VERIFIED 2026-09-14**: `RAIN_PROVIDER=openmeteo` → 1328 rows/source, ~1.6s/call, fresh stamps; failures go STALE, never mocked |
| Soil moisture | **SIMULATED** (rain-derived proxy, seeded deterministic). Live path is **MODELED** reanalysis (`OPENMETEO_MODELED`) — tagged `soil_moisture_source=MODELED`, never called observed/SMAP |
| Satellite / SAR | **SATELLITE_DEMO** — random mock values, **excluded from production risk** (neutral constant). No live Sentinel path (`SATELLITE_LIVE=false`) |
| Terrain | **STATIC** — 8 hardcoded Meghalaya zone profiles (no DEM pipeline yet) |
| History | **STATIC** seed (10 demo events) + **REAL** ERA5 sequences: `seq_real_v1` (24) → `seq_real_v2` (32, +8 hard peak-rain no-event negatives). Mamba on REAL data: v03 F1 0.50 / v04 F1 0.444 (recall 1.0), GroupKFold CV 0.489±0.126 — EXPERIMENTAL, gate BLOCKED. Static CV: LogReg 0.53 / GBM 0.50 / RF 0.38 (all DEMO). Simulated Mamba F1 0.94 = pipeline proof only. Production RF on 8 zone labels (F1-macro 0.22, DEMO) |
| Terrain | STATIC profiles (legacy RF path) + **OBSERVED** SRTM30m: per-zone derivatives + 9×9@250m grids → `/risk/{z}/cell-grid` mode=observed (honest sub-zone-blindness note) |
| Satellite | DEMO risk path + **OBSERVED** catalog metadata: 10 real S1 acquisitions via ASF (no imagery — 403 auth boundary proven, no risk use) |
| Temporal model | **FALLBACK** — heuristic baseline. Untrained Mamba is **excluded** from the risk path (`MAMBA_LIVE=false`, no weights) |
| Confidence | **Uncalibrated** mean(static, dynamic) — labeled `confidence_basis`, not a probability |
| XAI | **IMPORTANCE_WEIGHTED / HEURISTIC** driver bars (RF importances × local deviation) — not SHAP (never claimed) |
| Alerts | **MOCK DELIVERY** (SMS + email, logged only) + threshold engine + cooldown/dedup + escalation + ack/resolve + audit; EN/HI reviewed, AS/MNI fall back to EN |
| ML evidence | `models/registry.json` — LogReg vs RF on `events_v2`, Platt calibration attempt, Brier scores; `/admin/model/metrics` serves measured values only (fabricated hardcodes removed) |
| Real-time | **PERIODIC / on-demand**, not streaming (worker every 15 min; dashboard recomputes per request) |
| Offline | **OFFLINE FIELD REPORTING only** (IndexedDB queue + SW shell cache), not full offline app |
| Mobile | Responsive web field form, **not** a native app |
| 3D | **Not implemented** — map "3D*" button is a visual tilt only |
| Auth | Role keys (`API_KEYS="k:admin,k:operator,k:viewer"`, server-side `require_role`) on send/evaluate/ack/resolve/moderation; Fernet SecretBox for `ENC:` secrets; otherwise open-demo in development (labeled). `ENVIRONMENT=production` with no keys fails closed (401); `CORS_ORIGINS=*` is development-only, production requires explicit origins. Uploads: MIME + magic-byte + size + sha256-dedup |
| Observability | `/health` `/ready` `/api/data-status` `/api/worker-status` `/api/model/monitor` `/api/gis/provenance` — no secrets exposed |

## Quickstart (demo)

```bash
# backend
cd backened && python -m uvicorn app.main:app --port 8000
# worker (separate process — real worker, not a second API server)
python worker.py
# frontend
cd frontend && npm i && npm run dev
```

Docker: `docker compose up --build` (backend + **worker** + frontend + healthchecks). Compose shares one sqlite file between backend and worker via the `sqlite_data:/data` volume (`DATABASE_URL=sqlite:////data/geo_sentinel.db`); local relative sqlite URLs resolve against `backened/` independent of CWD. Terrain/training sources mount read-only at `/datasets` (without it gs endpoints honestly return 503). Prod runtime VERIFIED 2026-09-15: `--profile prod` + Postgres DATABASE_URL override → PostgreSQL 16.4 + PostGIS 3.4, migrate v1–v8, full E2E + outage recovery (see `docs/POSTGRES_POSTGIS.md`). Compose runtime VERIFIED 2026-09-18 (build + healthy up + 27/27 API checks + restart/down-up recovery + browser E2E PASS + Postgres prod-profile runtime) — see `reports/FINAL_RUNTIME_VERIFICATION.md`.

## Live rainfall (optional, unverified)

```
RAIN_PROVIDER=openmeteo  OPENMETEO_TIMEOUT_S=15
```

Then check `GET /api/data-status` → rainfall `LIVE` after first successful run, else `STALE`
(never silently mocked). Satellite stays demo regardless.

## Key endpoints

- `GET /api/data-status` — provider/model/delivery honesty card
- `GET /api/ready`, `/health` — readiness
- `POST /api/alerts/evaluate` — threshold + cooldown auto-evaluation (worker calls this)
- `POST /api/alerts/send` — guarded manual dispatch (HIGH/VERY_HIGH only)
- `POST /api/reports` + `/reports/{id}/media` (JPEG/PNG/WEBP/MP4/WEBM, magic-byte checked) + moderation
- Sensors: `POST /api/sensors/soil-moisture`, `POST /api/sensors/readings` (soil/rain/tilt/pore-pressure, dup+outlier handled) + `GET /api/sensors` (ONLINE/STALE/OFFLINE)
- Satellite boundary: `GET /api/satellite/status`, `/satellite/scenes`, `POST /api/satellite/change` (demonstrable delta, quarantined from risk)
- `GET /api/risk/{z}/rainfall-windows` (1/3/6/12/24/72h/7d + intensity + antecedent, Observed/Modeled/Scenario labeled)
- `GET /api/landslides/inventory` (temporal-trainable vs spatial display-only split) + `GET /api/exposure/villages` (villages + infra registry)
- `GET /api/models` (versions + promotion gates), `GET /api/metrics`, `GET /api/alerts/languages`
- Pages: `/sensors`, `/satellite`, `/health` alongside command center, reports, alerts, roads, weather, emergency, insights
- gs_v1 model assessments (OpenAPI `GsOut`: `risk_score`/`temporal_risk` nullable): `GET /api/risk/gs_point?lat=..&lon=..`, `POST /api/risk/gs_tabular`, `POST /api/risk/gs_sequence`. Invalid input returns 422, missing model artifact returns 503. The zone tab renders a live `GsPointPanel` (real API, explicit AVAILABLE/UNAVAILABLE/ERROR states; temporal prediction shown as unavailable — Mamba chance-level, unwired)
- Provider switches: `WEATHER_PROVIDER=mock|openmeteo|imd`, `SOIL_PROVIDER=demo|modeled|smap|sensor`, `SATELLITE_PROVIDER=demo|sentinel1`, `PUSH_PROVIDER=mock|fcm` (see `backened/.env.example`); compliance matrix: `docs/SIH_FINAL_COMPLIANCE_REPORT.md`

## NER training pipeline (reproducible, honest)

```
cd backened
python scripts/ingest_gsi.py            # GSI mirror (COOLR: egress-blocked, --manual supported)
python scripts/build_inventory.py       # NER filter + date classes + dedup → ner_inventory
python scripts/build_controls.py        # matched NO_RECORDED_LANDSLIDE controls
python scripts/fetch_rainfall.py        # Open-Meteo archive windows (REAL)
python scripts/ingest_dem.py            # SRTM 5x5 windows (REAL)
python scripts/ingest_sentinel1.py      # ASF metadata discovery (REAL metadata, no imagery)
python scripts/ingest_osm.py            # Overpass road counts (REAL)
python scripts/build_features.py        # provenance + missingness per value
python scripts/build_training_dataset.py --region NER --version ner_v1
python scripts/run_leakage_checks.py --version ner_v1   # binding gates
python scripts/train_models.py --dataset ner_v1         # LogReg → RF → GBM (EXPERIMENTAL, gate-BLOCKED)
python scripts/evaluate_models.py --dataset ner_v1
python scripts/final_dataset_audit.py   # mandated audit block (Status: PARTIAL)
```

SMAP/NRSC/COOLR contribute when their access conditions are met
(`EARTHDATA_*`, `data/manual/*`, full egress); failures are reported, never
fatal. Details: `docs/NER_DATASET_FINAL_REPORT.md`, `docs/ML_FINAL_REPORT.md`.

## Tests

`cd backened && python -m pytest` (test counts grow with the suite — run it
for the current number; includes `tests/test_sih_chain.py`,
`test_training_leakage.py`, `test_ner_pipeline.py`, routing-safety,
error-contract, RF-validation, media-security, rate-limit, observability
regressions, plus `test_hardening.py` and `test_db_shared_persistence.py`) · regression gate: `python scripts/final_verify.py` (20 checks, 0 FAIL; postgis check probes a live compose postgres when present) · temporal gates: `validate_temporal_dataset.py [--v2]` · Mamba: `train_mamba_real [--v2]`, `cv_mamba`, `benchmark_real` · DEM: `fetch_dem.py` + `fetch_demgrid.py` · sat: `fetch_satmeta.py` · hard negs: `fetch_temporal.py --fetch-hard`, build `--build --v2` · live: `LIVE_NET_TEST=1 pytest tests/test_pipeline.py::test_live_openmeteo_ingestion_verified` · dataset gate: `python scripts/validate_dataset.py` · dataset build: `python data/process_events.py` · Mamba train: `python -m app.ml.train_mamba` · retraining gate: `python scripts/promote_reports.py --list` · `cd frontend && npm test -- --run` (run for the current count; covers gs
null-state, formatter, rescue, XSS popup, backend-status, basemap utils) · `npx tsc --noEmit` clean · `npm run build` ok. Docker compose runtime unverified here (daemon down); backend Dockerfile runs `scripts/migrate.py` (versioned v1–v8) on boot. Fusion weights: single source `backened/risk_thresholds.yaml` (compose sets no overrides).

## Demo script (deterministic, ~5 min)

1. Dashboard → Data Status bar shows SIMULATED/STATIC chips (or LIVE after `RAIN_PROVIDER=openmeteo` + worker run). 2. Scrub monsoon timeline → rainfall/soil react. 3. Select Z1 (Sohra) → evidence: scores, 24/72h/7d rain, soil, slope, history, vulnerable roads, active alerts, freshness. 4. Drivers show `PERMUTATION_IMPORTANCE` method. 5. Hotspots → emergency priorities (population-weighted). 6. Evacuation panel → lower-exposure vs baseline route + why. 7. Submit field report (photo) → Reports → VERIFIED → USED_FOR_TRAINING. 8. Trigger HIGH alert → cooldown blocks dup → escalate VERY_HIGH → ack → resolve → audit trail. 9. `/api/model/reliability` + registry show measured (weak) metrics. 10. Docs: `docs/FINAL_SCORE_REPORT.md` for the evidence behind every number.

## Roadmap (not claimed as done)

Live IMD/SMAP keys, real Sentinel imagery ingestion, full-raster DEM/curvature pipeline, larger curated landslide inventory
with spatial train/val/test + calibrated probabilities, trained temporal checkpoint passing promotion
gates, live SMS/push delivery runs, full PWA with offline maps, verified Postgres/PostGIS runtime + S3, JWT roles, CI. (Redis is explicitly out of scope — in-memory rate limiting by design.)
